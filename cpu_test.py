import psutil
import time

PROCNAME1 = "celery"
PROCNAME2 = "rabbitmq"


def test():
    for i in range(1000):
        time.sleep(3)
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME1 or PROCNAME2:
                a = proc.pid
                p = psutil.Process(a)
                print(proc.name())
                print(p.status)
                print(p.cpu_percent(interval=1))
                print(p.cpu_affinity())