from django.conf.urls import include, url


urlpatterns = [
    url(r'^', include('main.urls')),
    url(r'^admin/', include('local_admin.urls')),
    url(r'^local-admin/', include('company_admin.urls')),
    url(r'^user/', include('users.urls')),
]