from django.urls import path

from . import views

urlpatterns = [
    #path(r'^search/', include('haystack.urls')),
    path('', views.index, name='index'),
]
