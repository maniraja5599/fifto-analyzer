"""
API endpoints for market data - Enhanced with NSE integration
"""
import os
import json
from datetime import datetime, time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .market_data import get_market_data, get_market_status  # uses unified dhan_api internally now
from .historical_data import historical_fetcher

# Import enhanced market data with NSE support
try:
    from .market_data_enhanced import get_enhanced_market_data, test_data_sources
    ENHANCED_DATA_AVAILABLE = True
except ImportError:
    ENHANCED_DATA_AVAILABLE = False

# Import yfinance market service (conditional to reduce background data fetching)
try:
    from django_market_service import get_django_market_data, get_django_historical_data
    YFINANCE_AVAILABLE = True
    print("📊 YFinance service available - will use on-demand only")
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ YFinance service not available, falling back to DhanHQ")

@csrf_exempt
@require_http_methods(["GET"])
def market_data_api(request):
    """
    API endpoint to get real-time market data from live market service
    """
    try:
        # Read directly from the live market service cache
        cache_file = os.path.join(settings.BASE_DIR, 'market_data_cache.json')
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                
            # Extract market data
            market_data = {
                'NIFTY': cache_data.get('NIFTY', {}),
                'BANKNIFTY': cache_data.get('BANKNIFTY', {})
            }
            
            # Check market hours
            now = datetime.now().time()
            market_open = time(9, 15)  # 9:15 AM
            market_close = time(15, 30)  # 3:30 PM
            is_market_open = market_open <= now <= market_close
            
            response_data = {
                'success': True,
                'market_status': {
                    'is_open': is_market_open,
                    'status': 'LIVE' if is_market_open else 'CLOSED'
                },
                'market_data': market_data,
                'timestamp': cache_data.get('timestamp', ''),
                'source': cache_data.get('source', 'live_market_service'),
                'cache_status': 'active'
            }
        else:
            # Fallback data if cache doesn't exist
            response_data = {
                'success': True,
                'market_status': {'is_open': False, 'status': 'CLOSED'},
                'market_data': {
                    'NIFTY': {'current_price': 24500.0, 'change': 0, 'change_percent': 0},
                    'BANKNIFTY': {'current_price': 51000.0, 'change': 0, 'change_percent': 0}
                },
                'timestamp': datetime.now().isoformat(),
                'source': 'fallback',
                'cache_status': 'no_cache'
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
            'error': str(e),
            'market_data': {
                'NIFTY': {'current_price': 0, 'change': 0, 'change_percent': 0},
                'BANKNIFTY': {'current_price': 0, 'change': 0, 'change_percent': 0}
            }
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
    API endpoint to get historical market data for charts using yfinance
    """
    try:
        # Get parameters
        symbol = request.GET.get('symbol', 'NIFTY')
        period = request.GET.get('period', '1mo')  # 1d, 5d, 1mo, 3mo, etc.
        
        if YFINANCE_AVAILABLE:
            # Start market service only when historical data is actually requested
            from django_market_service import start_market_service
            start_market_service()  # This will only start if not already running
            
            # Get historical data from yfinance service
            historical_data = get_django_historical_data(symbol, period)
            print(f"📊 Historical data fetched for {symbol} ({period}) - on-demand")
        else:
            # Fallback to empty data for now
            historical_data = []
            print("⚠️ Using fallback data - yfinance unavailable")
        
        response_data = {
            'success': True,
            'data': {symbol: historical_data},
            'period': period,
            'symbol': symbol,
            'timestamp': historical_data[-1].get('Date', '') if historical_data else '',
            'source': 'yfinance' if YFINANCE_AVAILABLE else 'fallback'
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

@csrf_exempt
@require_http_methods(["GET"])
def enhanced_market_data_api(request):
    """
    Enhanced API endpoint with multi-source market data (DhanHQ + NSE fallback)
    Supports source selection and testing
    """
    try:
        # Get optional source parameter
        force_source = request.GET.get('source', None)
        
        if ENHANCED_DATA_AVAILABLE:
            # Use enhanced market data with NSE fallback
            market_data = get_enhanced_market_data(force_source)
        else:
            # Fallback to original market data
            market_data = get_market_data()
        
        # Check market hours
        now = datetime.now().time()
        market_open = time(9, 15)  # 9:15 AM
        market_close = time(15, 30)  # 3:30 PM
        is_market_open = market_open <= now <= market_close
        
        response_data = {
            'success': True,
            'market_status': {
                'is_open': is_market_open,
                'status': 'LIVE' if is_market_open else 'CLOSED'
            },
            'market_data': {
                'NIFTY': {
                    'current_price': market_data.get('NIFTY', {}).get('price', 0),
                    'change': market_data.get('NIFTY', {}).get('change', 0),
                    'change_percent': market_data.get('NIFTY', {}).get('change_percent', 0),
                    'source': market_data.get('NIFTY', {}).get('source', 'unknown'),
                    'last_updated': market_data.get('NIFTY', {}).get('last_updated', '')
                },
                'BANKNIFTY': {
                    'current_price': market_data.get('BANKNIFTY', {}).get('price', 0),
                    'change': market_data.get('BANKNIFTY', {}).get('change', 0),
                    'change_percent': market_data.get('BANKNIFTY', {}).get('change_percent', 0),
                    'source': market_data.get('BANKNIFTY', {}).get('source', 'unknown'),
                    'last_updated': market_data.get('BANKNIFTY', {}).get('last_updated', '')
                }
            },
            'timestamp': datetime.now().isoformat(),
            'data_sources_available': ENHANCED_DATA_AVAILABLE,
            'forced_source': force_source
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
            'market_data': {
                'NIFTY': {'current_price': 0, 'change': 0, 'change_percent': 0, 'source': 'error'},
                'BANKNIFTY': {'current_price': 0, 'change': 0, 'change_percent': 0, 'source': 'error'}
            },
            'timestamp': datetime.now().isoformat()
        }, status=500)
        
        # Add cache-busting headers
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response

@csrf_exempt
@require_http_methods(["GET"])
def test_data_sources_api(request):
    """
    API endpoint to test all available data sources
    """
    try:
        if ENHANCED_DATA_AVAILABLE:
            test_results = test_data_sources()
        else:
            test_results = {'error': 'Enhanced data sources not available'}
        
        response_data = {
            'success': True,
            'test_results': test_results,
            'timestamp': datetime.now().isoformat()
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
            'timestamp': datetime.now().isoformat()
        }, status=500)
        
        # Add cache-busting headers
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
