# analyzer/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Main page for generating analysis
    path('', views.index, name='index'),

    # Form submission actions
    path('generate/', views.generate_and_show_analysis, name='generate_analysis'),
    path('add_trades/', views.add_trades, name='add_trades'),
    path('send_charts/', views.send_charts, name='send_charts'),

    # Pages for viewing data and settings
    path('trades/', views.trades_list, name='trades_list'),
    path('settings/', views.settings_view, name='settings'),

    # Action for closing a specific trade
    path('close_trade/<str:trade_id>/', views.close_trade, name='close_trade'),
]