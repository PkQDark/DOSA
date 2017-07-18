from django.conf.urls import url, include
from .views import site


urlpatterns = [
    url(r'^$', site, name='clion\clioff'),
]