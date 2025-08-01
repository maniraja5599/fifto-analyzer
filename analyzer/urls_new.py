# analyzer/urls.py - Clean New Implementation

from django.urls import path
from . import views_new

app_name = 'analyzer'

urlpatterns = [
    path('', views_new.index, name='index'),
    path('generate/', views_new.generate_charts, name='generate_charts'),
    path('settings/', views_new.settings_view, name='settings'),
    path('trades/', views_new.trades_view, name='trades'),
]
