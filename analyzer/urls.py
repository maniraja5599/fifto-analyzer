# analyzer/urls.py

from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    # Dashboard as default page
    path('', views.dashboard_view, name='dashboard'),
    
    # Analysis page
    path('analysis/', views.index, name='index'),

    # API endpoints
    path('api/market-data/', api_views.market_data_api, name='market_data_api'),
    path('api/market-status/', api_views.market_status_api, name='market_status_api'),
    path('api/historical-data/', api_views.historical_data_api, name='historical_data_api'),

    # Form submission actions
    path('generate/', views.generate_and_show_analysis, name='generate_analysis'),
    path('task_status/<str:task_id>/', views.check_task_status, name='check_task_status'),
    path('add_trades/', views.add_trades, name='add_trades'),
    path('send_charts/', views.send_charts, name='send_charts'),

    # Pages for viewing data and settings
    path('trades/', views.trades_list, name='trades_list'),
    path('closed_trades/', views.closed_trades_view, name='closed_trades'),
    path('automation/', views.automation_view, name='automation'),
    path('test_automation/', views.test_automation_view, name='test_automation'),
    path('settings/', views.settings_view, name='settings'),
    path('test_telegram/', views.test_telegram, name='test_telegram'),
    path('update_refresh_rate/', views.update_refresh_rate, name='update_refresh_rate'),

    # Action for closing a specific trade
    path('close_trade/<str:trade_id>/', views.close_trade, name='close_trade'),
]