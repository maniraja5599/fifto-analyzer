# analyzer/urls.py - Clean New Implementation

from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('', views.index, name='index'),
    path('generate/', views.generate_charts, name='generate_charts'),
    path('settings/', views.settings_view, name='settings'),
    path('trades/', views.trades_view, name='trades'),
]
