from django.conf.urls import include, url

from . import views

urlpatterns = [

    url(r'^$', views.index, name='ecfiddle_tool'),
    url(r'instructions$', views.instructions, name='instructions'),

]
