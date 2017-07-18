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
#13456
lock = threading.Lock()
kiev = timezone('Europe/Kiev')
logger = logging.getLogger('main')
BACKLOG = 50


class Comand:
    __flag = False
    __id_comand = {}
    __keys_list = {}
    __dev_id_list = []

    def __init__(self, *args):
        if len(args):
            send_text = args[0]
            if len(send_text) == 2:
                self.__flag = True
                self.__id_comand[send_text[0]] = send_text[1]
            if len(send_text) > 2:
                self.__flag = True
                self.__id_comand[send_text[0]] = send_text[1]
                for i in range(len(send_text) - 2):
                    self.__keys_list[send_text[i + 2]] = send_text[0]

    def check_flag(self):
        if self.__flag:
            return True
        else:
            return False

    def found_device(self, dev_id):
        if dev_id in list(self.__id_comand):
            return True
        return False

    def read_comand(self, dev_id):
        try:
            return self.__id_comand.pop(dev_id)
        except:
            return 0

    def destroy_key(self, key):
        self.__keys_list.pop(key)

    def comand_was_send(self):
        self.__flag = False
    
    def device_list(self):
        if len(self.__id_comand):
            return list(self.__id_comand)
        else:
            return 0

    def key_list(self):
        if len(self.__keys_list):
            return list(self.__keys_list)
        else:
            return 0
    
    def add_dev(self, dev_id):
        self.__dev_id_list.append(dev_id)

    def remove_dev(self, dev_id):
        self.__dev_id_list.remove(dev_id)

    def found_in_dev_list(self, dev_id):
        if dev_id in self.__dev_id_list:
            return True
        else:
            return False
 
    def done(self):
        return b'Create new comand is correct'


comand = Comand()


def read_keys_for_thread(sock, device):
    logger.info("into rkft")
    e = connect('clion\r', sock)
    if e == 'to_error':
        return 'error'
    time.sleep(2)
    text = connect('view keys\r', sock)
    logger.info('after VK send')
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
    logger.info('after clioff send')


def read_log_for_thread(sock, device):
    logger.info('In to rlft')
    e = connect('clion\r', sock)
    if e == 'to_error':
        return 'error'
    logger.info('clion was send')
    time.sleep(2)
    text = connect('view log\r', sock)
    logger.info('after VL send')
    num_of_total = text.find('Total,')
    text = text[num_of_total:]
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
    logger.info('after clioff send')


def import_keys_for_thread(sock, device):
    key_list = comand.key_list()
    e = connect('clion\r', sock)
    if e == 'to_error':
        return 'error'
    ans = b''
    time.sleep(1)
    for key in list(key_list):
        if len(key) == 16 and all(c in string.hexdigits for c in key):
            sock.send('import keys\r'.encode())
            time.sleep(2)
            logger.info('try to send IK to dev')
            n = b'\n'
            key_byte = key.encode()
            send_key = n + key_byte
            logger.info('Try send key - ' + repr(send_key))
            sock.send(send_key)
            time.sleep(1)
            ans += sock.recv(10240)
            logger.info('ans after keyinput - ' + repr(ans))
            time.sleep(1)
            logger.info('key ' + repr(key) + 'was sended')
        comand.destroy_key(key)
    connect('clioff\r', sock)
    logger.info('after clioff send')
    time.sleep(1)
    read_keys_for_thread(sock, device)


def connect(con_comand, sock):
    sock.send(con_comand.encode())
    logger.info('comand ' + repr(con_comand) + ' was send')
    answer = b''
    if con_comand == 'clion\r':
        try:
            answer += sock.recv(5000)
        except socket.timeout:
            logger.info('TO in clion')
            sock.close()
            return 'to_error'
        logger.info('Exit bcs comand is clion and trash is - ' + repr(answer))
        return
    if con_comand == 'clioff\r':
       logger.info('clioff')
       return
    logger.info('comand is no con or cof')
    while True:
        try:
            answer += sock.recv(10240)
            logger.info(' Answer in connect is ' + repr(answer))
        except socket.timeout:
            continue
        except UnicodeError:
            logger.info('UNICODE ERROR ' + repr(con_comand))
            continue
        if answer.endswith(b'DOSA-10W>'):
            break
    logger.info('answer before count and found - ' + repr(answer)) 
    if answer.count(b'DOSA-10W>') > 1:
        dosa = answer.find(b'DOSA-10W>\r')
        answer = answer[dosa:]
        logger.info('cut the string')
    return answer.decode()


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
    logger.info('keyowenr found')
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
        logger.info('send no')
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
        logger.info('send ack')
        t = sock.recv(12000)
        logger.info('Trash - ' + repr(t))


def wait_for_limit(sock, dev_id):
    input_text = b''
    global comand
    while not input_text.endswith(b'\r'):
        if comand.check_flag():
            if comand.found_device(dev_id):
                with lock:
                    logger.info('dev lock')
                    device = Device.objects.get(dev_id=dev_id)
                    logger.info('dev found')
                    cur_comand = comand.read_comand(dev_id)
                    r = '\r'
                    cur_comand += r
                    err = ''
                    if cur_comand == 'view_log\r':
                        err = read_log_for_thread(sock, device)
                    if cur_comand == 'view_keys\r':
                        err = read_keys_for_thread(sock, device)
                    if cur_comand == 'import_keys\r':
                        err = import_keys_for_thread(sock, device)
                    if err == 'error':
                        return 'error'
                    comand.comand_was_send()
                    logger.info('fl is false')
        try:
            input_text += sock.recv(1024)
            logger.info('Text in socket is - ' + repr(input_text))
        except socket.timeout:
            logger.info('TO')
            continue
        except UnicodeError:
            logger.info('Unicode error - for wfl')
            continue
    with lock:
        answer_to_limit(input_text, sock)
    wait_for_limit(sock, dev_id)


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
    global comand
    err = ''
    if len(parser_input) == 1:
        dev_id = parser_input[0]
        dev_id = dev_id[:dev_id.find(',')]
        comand.add_dev(dev_id)
        err = wait_for_limit(sock, dev_id)
        logger.info('Dev id now = ' + dev_id)
    if err == 'error':
        return
    if len(parser_input) >= 2:
        comand = Comand(parser_input)
        logger.info('found_device is ' + str(comand.found_in_dev_list(parser_input[0])))
        logger.info('device list now is ' + str(comand.device_list()))
        if comand.found_in_dev_list(parser_input[0]):
            sock.send(b'yes\r')
        else:
            sock.send(b'no\r')
        logger.info(repr(comand.done()))
        sock.close()
        return
    if len(dev_id):
        comand.remove_dev(dev_id)
    sock.close()
    logger.info('Done.')


def serve_forever(PORT):
    # создаём слушающий сокет
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # re-use port
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('',PORT))
    sock.listen(BACKLOG)
    # слушаем и при получении нового входящего соединения,
    # порождаем нить, которая будет его обрабатывать
    logger.info('Lis %s:%d...' % ('',PORT))
    while True:
        try:
            connection, (client_ip, client_port) = sock.accept()
            connection.settimeout(20)
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
def main(PORT):
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
    serve_forever(PORT)


p_9090 = 9090
p_9091 = 9091
main.delay(p_9090)
main.delay(p_9091)
