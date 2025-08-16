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
from .market_data import get_market_data, get_market_status  # uses NSE data only
from .historical_data import historical_fetcher

# Import enhanced market data with NSE support
try:
    from .market_data_enhanced import get_enhanced_market_data, test_data_sources
    ENHANCED_DATA_AVAILABLE = True
except ImportError:
    ENHANCED_DATA_AVAILABLE = False

# Import yfinance market service (conditional to reduce background data fetching)
try:
    from django_market_service import get_django_market_data, get_django_historical_data, manual_refresh_django_market_data
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
                'BANKNIFTY': cache_data.get('BANKNIFTY', {}),
                'SENSEX': cache_data.get('SENSEX', {}),
                'VIX': cache_data.get('VIX', {})
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
                    'BANKNIFTY': {'current_price': 51000.0, 'change': 0, 'change_percent': 0},
                    'SENSEX': {'current_price': 80000.0, 'change': 0, 'change_percent': 0},
                    'VIX': {'current_price': 15.0, 'change': 0, 'change_percent': 0}
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
                'BANKNIFTY': {'current_price': 0, 'change': 0, 'change_percent': 0},
                'SENSEX': {'current_price': 0, 'change': 0, 'change_percent': 0},
                'VIX': {'current_price': 0, 'change': 0, 'change_percent': 0}
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

@csrf_exempt
@require_http_methods(["POST"])
def manual_refresh_api(request):
    """
    API endpoint to manually refresh market data on-demand
    """
    try:
        if YFINANCE_AVAILABLE:
            print("🔄 Manual market data refresh requested via API...")
            fresh_data = manual_refresh_django_market_data()
            
            return JsonResponse({
                'success': True,
                'message': 'Market data refreshed successfully',
                'data': fresh_data,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Market data service not available',
                'message': 'Manual refresh service unavailable'
            }, status=503)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Manual refresh failed'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def refresh_trades_data_api(request):
    """
    API endpoint to manually refresh option chain data for active trades only
    Optimized to fetch only the strikes needed for current active trades
    """
    try:
        from . import utils
        from collections import defaultdict
        
        print("🔄 Manual trades data refresh requested...")
        
        # Load active trades
        trades = utils.load_trades()
        active_trades = [t for t in trades if t.get('status') == 'Running']
        
        if not active_trades:
            return JsonResponse({
                'success': True,
                'message': 'No active trades found',
                'data': {'nifty_strikes': [], 'banknifty_strikes': [], 'trades_updated': 0},
                'timestamp': datetime.now().isoformat()
            })
        
        # Check cache first for faster response
        cached_trades = utils.load_trades_data_cache(max_age_minutes=1)
        if cached_trades:
            print("💾 Using cached trades data for refresh")
            
        # Collect required strikes by instrument (only for visible/active trades)
        required_strikes = defaultdict(set)
        for trade in active_trades:
            instrument = trade.get('instrument', '')
            if instrument in ['NIFTY', 'BANKNIFTY']:
                ce_strike = trade.get('ce_strike')
                pe_strike = trade.get('pe_strike')
                if ce_strike:
                    required_strikes[instrument].add(float(ce_strike))
                if pe_strike:
                    required_strikes[instrument].add(float(pe_strike))
        
        # Fetch optimized option chain data
        option_chains = {}
        total_strikes_fetched = 0
        
        for instrument, strikes in required_strikes.items():
            if strikes:
                strikes_list = list(strikes)
                print(f"📡 Fetching {len(strikes_list)} strikes for {instrument}: {strikes_list}")
                chain_data = utils.get_option_chain_data_for_trades(instrument, strikes_list)
                if chain_data:
                    option_chains[instrument] = chain_data
                    total_strikes_fetched += len(strikes_list)
                    print(f"✅ Retrieved {len(strikes_list)} strikes for {instrument}")
        
        # Update trade P&L with fresh data
        trades_updated = 0
        total_pnl = 0
        
        for trade in active_trades:
            instrument = trade.get('instrument', '')
            chain_data = option_chains.get(instrument)
            
            if chain_data:
                current_ce, current_pe = 0.0, 0.0
                
                # Handle DhanHQ data structure
                if 'data' in chain_data and 'oc' in chain_data['data']:
                    oc_data = chain_data['data']['oc']
                    for strike_str, strike_data in oc_data.items():
                        try:
                            strike_price = float(strike_str)
                            
                            # Match CE (Call) data
                            if strike_price == trade.get('ce_strike') and 'ce' in strike_data:
                                current_ce = strike_data['ce'].get('last_price', 0.0)
                            
                            # Match PE (Put) data
                            if strike_price == trade.get('pe_strike') and 'pe' in strike_data:
                                current_pe = strike_data['pe'].get('last_price', 0.0)
                                
                        except (ValueError, KeyError):
                            continue
                
                # Calculate P&L
                if current_ce > 0 or current_pe > 0:
                    lot_size = utils.get_lot_size(trade['instrument'])
                    initial_premium = trade.get('initial_premium', 0)
                    current_premium = current_ce + current_pe
                    pnl = round((initial_premium - current_premium) * lot_size, 2)
                    
                    # Update trade data
                    trade['pnl'] = pnl
                    trade['current_premium'] = current_premium
                    total_pnl += pnl
                    trades_updated += 1
        
        # Save updated trades
        utils.save_trades(trades)
        
        # Cache the updated trades data for faster subsequent access
        utils.save_trades_data_cache(trades)
        
        # Prepare response
        nifty_strikes = list(required_strikes.get('NIFTY', []))
        banknifty_strikes = list(required_strikes.get('BANKNIFTY', []))
        
        response_data = {
            'nifty_strikes': nifty_strikes,
            'banknifty_strikes': banknifty_strikes,
            'total_strikes_fetched': total_strikes_fetched,
            'trades_updated': trades_updated,
            'total_pnl': total_pnl,
            'cache_status': 'updated'
        }
        
        print(f"✅ Trades data refresh complete: {trades_updated} trades updated, {total_strikes_fetched} strikes fetched")
        
        return JsonResponse({
            'success': True,
            'message': f'Trades data refreshed successfully - {trades_updated} trades updated',
            'data': response_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error refreshing trades data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Trades data refresh failed'
        }, status=500)
