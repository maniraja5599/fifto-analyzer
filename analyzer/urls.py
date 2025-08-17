# analyzer/urls.py

from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    # Analysis page as default (dashboard removed)
    path('', views.index, name='index'),
    
    # Analysis page (also accessible via /analysis/)
    path('analysis/', views.index, name='analysis'),

    # API endpoints
    path('api/market-data/', api_views.market_data_api, name='market_data_api'),
    path('api/enhanced-market-data/', api_views.enhanced_market_data_api, name='enhanced_market_data_api'),
    path('api/test-data-sources/', api_views.test_data_sources_api, name='test_data_sources_api'),
    path('api/market-status/', api_views.market_status_api, name='market_status_api'),
    path('api/historical-data/', api_views.historical_data_api, name='historical_data_api'),
    path('api/refresh-trades/', api_views.refresh_trades_data_api, name='refresh_trades_data_api'),
    path('api/manual-refresh/', api_views.manual_refresh_api, name='manual_refresh_api'),
    path('api/position-monitor-status/', api_views.position_monitor_status_api, name='position_monitor_status_api'),
    path('api/broker-accounts-status/', api_views.broker_accounts_status_api, name='broker_accounts_status_api'),
    
    # Basket Order APIs
    path('api/get-expiry-dates/', api_views.get_expiry_dates_api, name='get_expiry_dates_api'),
    path('api/get-option-prices/', api_views.get_option_prices_api, name='get_option_prices_api'),
    path('api/place-basket-order/', api_views.place_basket_order_api, name='place_basket_order_api'),

    # Form submission actions
    path('generate/', views.generate_and_show_analysis, name='generate_analysis'),
    path('task_status/<str:task_id>/', views.check_task_status, name='check_task_status'),
    path('add_trades/', views.add_trades, name='add_trades'),
    path('send_charts/', views.send_charts, name='send_charts'),
    path('place_live_orders/', views.place_live_orders, name='place_live_orders'),

    # Pages for viewing data and settings
    path('trades/', views.trades_list, name='trades_list'),
    path('closed_trades/', views.closed_trades_view, name='closed_trades'),
    path('automation/', views.automation_view, name='automation'),
    path('test_automation/', views.test_automation_view, name='test_automation'),
    path('settings/', views.settings_view, name='settings'),
    path('broker_settings/', views.broker_settings_view, name='broker_settings'),
    path('test_broker_connection/', views.test_broker_connection, name='test_broker_connection'),
    path('test_flattrade_quick/', views.test_flattrade_quick, name='test_flattrade_quick'),
    path('flattrade_oauth/', views.flattrade_oauth, name='flattrade_oauth'),
    path('flattrade_callback/', views.flattrade_callback, name='flattrade_callback'),
    path('flattrade_oauth_demo/', views.flattrade_oauth_demo, name='flattrade_oauth_demo'),
    path('nse-test/', views.nse_test_view, name='nse_test'),
    path('test_telegram/', views.test_telegram, name='test_telegram'),

    # Action for closing a specific trade
    path('close_trade/<str:trade_id>/', views.close_trade, name='close_trade'),
    
    # Option Chain and Basket Orders
    path('option_chain/', views.option_chain_view, name='option_chain'),
    path('set_option_chain_refresh/', views.set_option_chain_refresh, name='set_option_chain_refresh'),
    path('api/create_basket/', views.create_basket_order, name='create_basket_order'),
    path('basket_orders/', views.basket_orders_view, name='basket_orders'),
    path('api/clear_all_baskets/', views.clear_all_baskets, name='clear_all_baskets'),
]