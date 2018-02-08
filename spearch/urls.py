from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^search/', include('haystack.urls')),
    url('', views.index, name='index'),
]
