from django.urls import path
from . import views

# from perfreports import views as rept_view

urlpatterns = [
    path('', views.home, name="home"),
    path('options/', views.options, name='options'),
    path('pyscript/', views.pyscript, name='pyscript'),
    path('home/', views.home, name="home"),
    path('usstockpick/', views.usstockpick, name="usstockpick"),
    path('about/', views.about, name="about"),
    path('reports/', views.reports, name ='reports'),
    path('volreports/', views.volreports, name ='volreports'),
    path('performance/<str:filename>/', views.performance, name ='performance'),
    path('volatility/<str:filename>/', views.volatility, name ='volatility'),
    path('activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
        views.activate, name='activate'),
]
