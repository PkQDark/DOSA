from __future__ import absolute_import
import os
from celery import Celery
from datetime import timedelta
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DOSA_sim.settings')

app = Celery('serv', broker='amqp://', backend='amqp://', include =['serv.tasks'])
app.config_from_object('django.conf:settings')
# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.conf.update(
    result_expiries = 3600,
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

if __name__=='__main__':
    app.start()

