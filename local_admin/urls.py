from django.conf.urls import url
from .views import companies_list, add_company_view, edit_company_view, add_local_admin, local_admin_list, device_list, edit_device

urlpatterns = [
    url(r'^$', companies_list, name='companies'),
    url(r'^add-company/$', add_company_view, name='add_company'),
    url(r'^edit-company/((?P<company_id>\d+))/$', edit_company_view, name='edit_company'),
    url(r'^(?P<company_id>\d+)/add-admin/$', add_local_admin, name='la_add'),
    url(r'^local-admins/$', local_admin_list, name='la_list'),
    url(r'^devices-list/&', device_list, name='devs_list'),
    url(r'^devices-list/((?P<dev_id>\d+))/$', edit_device, name='edit_device'),
]