import psutil
import time


for i in range(1000):
    print(psutil.cpu_percent(interval=1))
    time.sleep(5)
