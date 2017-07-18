from __future__ import absolute_import
from local_admin.models import Device
from company_admin.models import KeyOwner, Cistern, Database, DayLimit, WeekLimit, MonthLimit
import errno
import threading
import socket
import logging
import time
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum
from pytz import timezone
import string
from .celery import app


lock = threading.Lock()
kiev = timezone('Europe/Kiev')
logger = logging.getLogger('main')
BIND_ADDRESS = ('', 9090)
BACKLOG = 50
THREAD_FLAG = False
ID_COMMAND = {}
KEY_LIST = {}


def read_keys_for_thread(sock, device):
    logger.info("into rkft")
    connect('clion\r', sock)
    logger.info('clion was send')
    time.sleep(2)
    text = connect('view keys\r', sock)
    logger.info('VK was send')
    text = text[0:-10]
    text = text.replace('\r', ' ')
    text = text.replace('\t', ' ')
    text = text.replace('\n', ' ')
    a = text.split(' ')
    temp_mas = []
    for i in range(len(a)):
        if a[i] != '':
            temp_mas.append(a[i])
    temp_mas = temp_mas[:-6]
    num_el = int((len(temp_mas)))
    num_str = int(num_el / 2)
    key_mas = []
    for i in range(num_str):
        key_mas.append([])
        for j in range(2):
            key_mas[i].append(temp_mas[i * 2 + j])
    for i in range(num_str):
        if key_mas[i][1] == 'FFFFFFFFFFFFFFFF':
            break
        KeyOwner.objects.get_or_create(keys=key_mas[i][1], defaults={'company': device.company})
    connect('clioff\r', sock)


def read_log_for_thread(sock, device):
    logger.info('In to rlft')
    connect('clion\r', sock)
    logger.info('clion was send')
    time.sleep(2)
    text = connect('view log\r', sock)
    logger.info('VL was send' + repr(text))
    text = text[0:-10]
    text = text.replace('\r', ' ')
    text = text.replace('\t', ' ')
    text = text.replace('\n', ' ')
    a = text.split(' ')
    temp_mas = []
    for i in range(len(a)):
        if a[i] != '':
            temp_mas.append(a[i])
    temp_mas = temp_mas[9:]
    num_el = int((len(temp_mas)))
    num_str = int(num_el / 8)
    mas = []
    for i in range(num_str):
        mas.append([])
        for j in range(8):
            mas[i].append(temp_mas[i * 8 + j])
    for i in range(num_str):
        us, created = KeyOwner.objects.get_or_create(keys=mas[i][1], company=device.company)
        devout, created = Database.objects.get_or_create(dev=device,
                                                         dosed=Decimal(mas[i][2]),
                                                         date_time=kiev.localize(
                                                             datetime.strptime(mas[i][4] + ' ' + mas[i][5],
                                                                               "%d.%m.%Y %H:%M")),
                                                         user=us)
        if created:
        # Recalculate cistern volumes
            previous = Database.objects.filter(dev=device,
                                               date_time__lt=devout.date_time).order_by('-date_time')
            if len(previous) > 0:
                previous_cist_volume = previous[0].cistern_volume
            else:
                previous_cist_volume = device.cistern.start_volume
            devout.cistern_volume = previous_cist_volume - devout.dosed + devout.add
            next_cist_dosings = Database.objects.filter(dev=device,
                                                        date_time__gt=devout.date_time).order_by('date_time')
            if len(next_cist_dosings):
                previous_cist_volume = devout.cistern_volume
                for load in next_cist_dosings:
                    load.cistern_volume = previous_cist_volume - load.dosed + load.add
                    previous_cist_volume = load.cistern_volume
                    load.save()
            # Recalculate fuel volumes
            by_fuel = Database.objects.filter(date_time__lt=devout.date_time,
                                              dev__cistern__fuel=device.cistern.fuel).order_by('-date_time')
            if len(by_fuel) > 0:
                previous_fuel_volume = by_fuel[0].fuel_volume
            else:
                fuel_cists = Cistern.objects.filter(fuel=device.cistern.fuel)
                previous_fuel_volume = fuel_cists.aggregate(Sum('start_volume'))['start_volume__sum']
            devout.fuel_volume = previous_fuel_volume - devout.dosed + devout.add
            devout.save()
            next_dosings = Database.objects.filter(date_time__gt=devout.date_time,
                                                   dev__cistern__fuel=device.cistern.fuel).order_by('date_time')
            if len(next_dosings):
                previous_fuel_volume = devout.fuel_volume
                for load in next_dosings:
                    load.fuel_volume = previous_fuel_volume - load.dosed + load.add
                    previous_fuel_volume = load.fuel_volume
                    load.save()
    connect('clioff\r', sock)


def import_keys_for_thread(sock, device):
    global KEY_LIST
    connect('clion\r', sock)
    ans = b''
    time.sleep(2)
    for key in list(KEY_LIST):
        if len(key) == 16 and all(c in string.hexdigits for c in key):
            sock.send('import keys\r'.encode())
            time.sleep(2)
            logger.info('try to send IK to dev')
            n = b'\n'
            key_byte = key.encode()
            send_key = n + key_byte
            logger.info('Try send key - ' + repr(send_key))
            sock.send(send_key)
            time.sleep(2)
            ans += sock.recv(102400)
            logger.info('ans after keyinput - ' + repr(ans))
            time.sleep(2)
            logger.info('key ' + repr(key) + 'was sended')
        KEY_LIST.pop(key)
    connect('clioff\r', sock)
    time.sleep(5)
    read_keys_for_thread(sock, device)


def connect(comand, sock):
    sock.send(comand.encode())
    logger.info('comand ' + repr(comand) + ' was send')
    time.sleep(2)
    logger.info('1st - send comand ' + comand)
    if comand == 'clion\r' or comand == 'clioff\r':
        sock.send(comand.encode())
        time.sleep(2)
        logger.info('comand ' + repr(comand) + ' was send')
        logger.info('2nd - send comand ' + comand)
    answer = b''
    if comand == 'clioff\r':
        logger.info('Exit bcs comand is clioff')
        return
    flag = True
    while not answer.endswith(b'DOSA-10W>'):
        try:
            answer += sock.recv(1024)
            logger.info('Try answer is - ' + repr(answer))
            if comand == 'clion\r' and answer.endswith(b'DOSA-10W>'):
                logger.info('exit 10W>')
                return
            answer.decode()
        except socket.timeout:
            connect(comand, sock)
        except UnicodeError:
            flag = False
            time.sleep(1)
            logger.info('UNICODE ERROR ' + repr(comand))

        logger.info('answer is - ' + repr(answer))
    if flag:
        logger.info('All answer is - ' + answer.decode())
        return answer.decode()
    else:
        connect(comand, sock)


def add_comand(parser_text, sock):
    global THREAD_FLAG
    global ID_COMMAND
    global KEY_LIST
    if len(parser_text) == 2:
        logger.info('after parce 2')
        THREAD_FLAG = True
        ID_COMMAND[parser_text[0]] = parser_text[1]
        sock.close()
        return
    if len(parser_text) > 2:
        logger.info('after parce >2')
        THREAD_FLAG = True
        ID_COMMAND[parser_text[0]] = parser_text[1]
        for i in range(len(parser_text) - 2):
            KEY_LIST[parser_text[i + 2]] = parser_text[0]
        sock.close()
        return


def answer_to_limit(input_text, sock):
    if input_text.find(b'.00'):
        input_text = input_text[:input_text.find(b'.00') + 3]
    else:
        logger.info('Bad command')
        return
    logger.info('decode text in sock - ' + repr(input_text))
    text = input_text.decode()
    logger.info('In limit ans')
    a = text.split(' ')
    a[1] = a[1][-16:]
    logger.info('Key is - ' + a[1])
    k = KeyOwner.objects.get(keys=a[1])
    dl = hasattr(k, 'daylimit')
    block_dl = False
    if hasattr(k, 'daylimit'):
        k.daylimit.recalc()
        if k.daylimit.cur_volume < Decimal(a[3][:-1]):
            block_dl = True
    wl = hasattr(k, 'weeklimit')
    block_wl = False
    if hasattr(k, 'weeklimit'):
        k.weeklimit.recalc()
        if k.weeklimit.cur_volume < Decimal(a[3][:-1]):
            block_wl = True
    ml = hasattr(k, 'monthlimit')
    block_ml = False
    if hasattr(k, 'monthlimit'):
        k.monthlimit.recalc()
        if k.monthlimit.cur_volume < Decimal(a[3][:-1]):
            block_ml = True
    time.sleep(2)
    if block_dl or block_wl or block_ml:
        sock.send('no\r'.encode())
    else:
        if dl and not block_dl:
            d_lim = DayLimit.objects.get(key_owner=k)
            d_lim.cur_volume -= Decimal(a[3][:-1])
            d_lim.save()
        if wl and not block_wl:
            w_lim = WeekLimit.objects.get(key_owner=k)
            w_lim.cur_volume -= Decimal(a[3][:-1])
            w_lim.save()
        if ml and not block_ml:
            m_lim = MonthLimit.objects.get(key_owner=k)
            m_lim.cur_volume -= Decimal(a[3][:-1])
            m_lim.save()
        sock.send('ack\r'.encode())
        t = sock.recv(12000)
        logger.info('Trash - ' + repr(t))


def wait_for_limit(sock, dev_id):
    input_text = b''
    logger.info('In WFL')
    global THREAD_FLAG
    global ID_COMMAND
    global KEY_LIST
    while not input_text.endswith(b'\r'):
        if input_text.endswith(b'\n'):
            logger.info('text is - ' + repr(input_text))
            decode_text = input_text.decode()
            parser_text = decode_text.split()
            if len(parser_text) >= 2:
                add_comand(parser_text, sock)
        try:
            input_text += sock.recv(1024)
            logger.info('looking for text')
        except socket.timeout:
            logger.info('timeout error')
            if THREAD_FLAG:
                logger.info('Flag is true!!!')
                if dev_id in list(ID_COMMAND):
                    with lock:
                        logger.info('Devise is found!!!')
                        device = Device.objects.get(dev_id=dev_id)
                        comand = ID_COMMAND.pop(dev_id)
                        logger.info('doing ' + comand)
                        r = '\r'
                        comand += r
                        if comand == 'view_log\r':
                            logger.info('comand is VL')
                            read_log_for_thread(sock, device)
                        if comand == 'view_keys\r':
                            logger.info('comand is VK')
                            read_keys_for_thread(sock, device)
                        if comand == 'import_keys\r':
                            logger.info('comand is IK')
                            import_keys_for_thread(sock, device)
                        THREAD_FLAG = False
                    wait_for_limit(sock, dev_id)
                else:
                    wait_for_limit(sock, dev_id)
            else:
                wait_for_limit(sock, dev_id)
        except UnicodeError:
            logger.info('Unicode error - for wfl')
            wait_for_limit(sock, dev_id)
    answer_to_limit(input_text, sock)


def handle(sock, client_ip, client_port):
    # обработчик, работающий в процессе-потомке
    logger.info('in handle')
    logger.info('Start to process request from %s:%d' % (client_ip, client_port))
    # получаем все данные до перевода строки
    in_buffer = b''
    while not in_buffer.endswith(b'\n'):
        in_buffer += sock.recv(1024)
    logger.info('In buffer = ' + repr(in_buffer))
    decode_input = in_buffer.decode()
    parser_input = decode_input.split()
    dev_id = ''
    if len(parser_input) == 1:
        dev_id = parser_input[0]
        dev_id = dev_id[:dev_id.find(',')]
    logger.info('Dev id now = ' + dev_id)
    if len(parser_input) >= 2:
        add_comand(parser_input, sock)
    wait_for_limit(sock, dev_id)
    sock.close()
    logger.info('Done.')


def serve_forever():
    # создаём слушающий сокет
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # re-use port
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(BIND_ADDRESS)
    sock.listen(BACKLOG)
    # слушаем и при получении нового входящего соединения,
    # порождаем нить, которая будет его обрабатывать
    logger.info('Listening no %s:%d...' % BIND_ADDRESS)
    while True:
        try:
            connection, (client_ip, client_port) = sock.accept()
            connection.settimeout(10)
            logger.info('Try connection')
        except IOError as e:
            if e.errno == errno.EINTR:
                continue
            raise
        # запускаем нить
        thread = threading.Thread(
            target=handle,
            args=(connection, client_ip, client_port)
        )
        thread.daemon = True
        logger.info('thread daemon')
        thread.start()


@app.task
def main():
    # настраиваем логгинг
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(thread)s] %(message)s',
        '%H:%M:%S'
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.info('Run')
    # запускаем сервер
    serve_forever()

main.delay()

