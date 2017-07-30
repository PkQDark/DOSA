import psutil
import time
import datetime

PROCNAME = "celery"


def test():
    cpu = 5.0
    report = open("cpu_report.txt", "w")
    while cpu <= 100.0:
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME:
                    a = proc.pid
                    p = psutil.Process(a)
                    cpu_lvl = p.cpu_percent(interval=1)
                    if cpu_lvl >= cpu:
                        report.write("Name process " + p.name() + " cpu = " + cpu_lvl + " date and time = " + str(datetime.datetime.now()) + "\n")
        time.sleep(60)
    report.close()

test()