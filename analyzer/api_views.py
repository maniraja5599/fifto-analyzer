"""
API endpoints for market data
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .market_data_v2 import get_market_data, get_market_status  # uses unified dhan_api internally now
from .historical_data import historical_fetcher

@csrf_exempt
@require_http_methods(["GET"])
def market_data_api(request):
    """
    API endpoint to get real-time market data with cache-busting headers
    """
    try:
        market_data = get_market_data()
        market_status = get_market_status()
        
        response_data = {
            'success': True,
            'market_status': market_status,
            'market_data': {
                'nifty': market_data.get('NIFTY', {}),
                'banknifty': market_data.get('BANKNIFTY', {}),
                'sensex': market_data.get('SENSEX', {}),
                'vix': market_data.get('VIX', {})
            },
            'timestamp': market_data.get('NIFTY', {}).get('last_updated', ''),
            'source': 'DhanHQ API v2'
        }
        
        response = JsonResponse(response_data)
        
        # Add cache-busting headers to prevent browser caching
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
        
    except Exception as e:
        response = JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        
        # Add cache-busting headers even for error responses
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response

@csrf_exempt
@require_http_methods(["GET"])
def market_status_api(request):
    """
    API endpoint to get market status
    """
    try:
        market_status = get_market_status()
        return JsonResponse({
            'success': True,
            'market_status': market_status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def historical_data_api(request):
    """
    API endpoint to get historical market data for charts
    """
    try:
        # Get parameters
        symbols = request.GET.get('symbols', 'NIFTY,BANKNIFTY,SENSEX').split(',')
        period = request.GET.get('period', '1d')  # 1d, 5d, 1mo, etc.
        interval = request.GET.get('interval', '5m')  # 1m, 5m, 15m, etc.
        
        # Fetch historical data
        historical_data = historical_fetcher.get_multiple_historical(
            symbols=symbols,
            period=period, 
            interval=interval
        )
        
        response_data = {
            'success': True,
            'data': historical_data,
            'period': period,
            'interval': interval,
            'symbols': symbols,
            'timestamp': historical_data.get(symbols[0], {}).get('last_updated', '') if historical_data else '',
            'source': 'yfinance + DhanHQ fallback'
        }
        
        response = JsonResponse(response_data)
        
        # Add cache-busting headers
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
        
    except Exception as e:
        response = JsonResponse({
            'success': False,
            'error': str(e),
            'data': {}
        }, status=500)
        
        # Add cache-busting headers even for error responses
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
