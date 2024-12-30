# rebalance/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('portweights/', views.portweights, name='portweights'),
    path('weights/', views.weights_by_port_name, name='weights_by_port_name'),
    path('get_weights_details/', views.get_weights_details, name='get_weights_details'),
]
