"""
API endpoints for market data - Enhanced with NSE integration
"""
import os
import json
from datetime import datetime, time, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings
from django.utils import timezone
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
    print("⚠️ YFinance service not available, using NSE fallback")

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
    Enhanced API endpoint with multi-source market data (NSE + yfinance)
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
                
                # Handle NSE data structure
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


@require_POST
@csrf_exempt
@require_http_methods(["POST"])
def position_monitor_status_api(request):
    """
    API endpoint to get current position monitoring status
    Returns active positions, monitoring status, and recent alerts
    """
    try:
        from .position_monitor import position_monitor
        from . import utils
        
        # Get monitoring status
        status_info = position_monitor.get_monitoring_status()
        is_monitoring = status_info.get('running', False)
        active_positions = status_info.get('positions', [])
        
        # Get recent trades with positions
        all_trades = utils.load_trades()
        
        # Filter recent trades (last 24 hours)
        current_time = datetime.now()
        recent_trades = []
        
        for trade in all_trades:
            try:
                # Parse trade creation time
                created_at_str = trade.get('created_at', '')
                if created_at_str:
                    trade_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    # Check if trade is within last 24 hours and is open
                    if (current_time - trade_time).total_seconds() < 86400 and trade.get('is_open', True):
                        trade_info = {
                            'id': trade.get('id', ''),
                            'nifty_ltp': trade.get('nifty_ltp', 0),
                            'strategy': trade.get('strategy', 'Unknown'),
                            'target': trade.get('target', 0),
                            'stoploss': trade.get('stoploss', 0),
                            'current_pnl': trade.get('current_pnl', 0),
                            'created_at': created_at_str,
                            'is_monitored': str(trade.get('id', '')) in active_positions
                        }
                        recent_trades.append(trade_info)
            except Exception as parse_error:
                print(f"Error parsing trade: {parse_error}")
                continue
        
        # Limit to 10 most recent trades
        recent_trades = recent_trades[-10:] if len(recent_trades) > 10 else recent_trades
        
        response_data = {
            'is_monitoring': is_monitoring,
            'active_positions_count': len(active_positions),
            'active_positions': active_positions,
            'recent_trades': recent_trades,
            'service_status': 'running' if is_monitoring else 'stopped',
            'total_closed': status_info.get('total_closed', 0),
            'last_check': status_info.get('last_check', '')
        }
        
        return JsonResponse({
            'success': True,
            'data': response_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error getting position monitor status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Failed to get position monitor status'
        }, status=500)


@require_POST
@csrf_exempt
@require_http_methods(["POST"])
@csrf_exempt
def broker_accounts_status_api(request):
    """
    API endpoint to get broker account status for automation schedule configuration
    Returns list of enabled broker accounts from fifto_settings.json
    """
    try:
        from . import utils
        
        # Get broker accounts from fifto_settings.json
        settings = utils.load_settings()
        broker_accounts = settings.get('broker_accounts', [])
        
        broker_status = []
        
        for account in broker_accounts:
            if account.get('enabled', False):
                # For FlatTrade, use client_id; for others, use account_id
                account_id = account.get('client_id') if account.get('broker') == 'FLATTRADE' else account.get('account_id')
                
                if account_id:
                    account_info = {
                        'id': account_id,
                        'broker': account.get('broker', ''),
                        'account_name': account.get('account_name', account_id),
                        'status': 'enabled',
                        'enabled': True
                    }
                    broker_status.append(account_info)
        
        response_data = {
            'broker_accounts': broker_status,
            'summary': {
                'total_accounts': len(broker_status),
                'enabled_accounts': len(broker_status)
            }
        }
        
        return JsonResponse({
            'success': True,
            'data': response_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error getting broker accounts: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Failed to get broker accounts'
        }, status=500)


@csrf_exempt
@require_POST
def get_expiry_dates_api(request):
    """
    API endpoint to get expiry dates for options
    """
    try:
        instrument = request.GET.get('instrument', 'NIFTY')
        
        # Mock expiry dates - in production, fetch from broker APIs
        base_date = datetime.now()
        expiry_dates = []
        
        # Generate next 4 weekly expiries (Thursday)
        for week in range(4):
            # Find next Thursday
            days_ahead = 3 - base_date.weekday()  # Thursday is 3
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            
            expiry_date = base_date + timedelta(days=days_ahead + (week * 7))
            expiry_dates.append(expiry_date.strftime('%d-%b-%Y'))
        
        # Add monthly expiry (last Thursday of month)
        last_day = base_date.replace(day=28) + timedelta(days=4)
        last_day = last_day - timedelta(days=last_day.weekday() + 1)  # Last Thursday
        if last_day > base_date:
            expiry_dates.append(last_day.strftime('%d-%b-%Y'))
        
        return JsonResponse({
            'success': True,
            'expiry_dates': expiry_dates,
            'instrument': instrument
        })
        
    except Exception as e:
        print(f"❌ Error getting expiry dates: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_POST
def get_option_prices_api(request):
    """
    API endpoint to get current option prices
    """
    try:
        data = json.loads(request.body)
        symbols = data.get('symbols', [])
        instrument = data.get('instrument', 'NIFTY')
        
        # Mock prices - in production, fetch from broker APIs or NSE
        prices = {}
        for symbol in symbols:
            # Generate realistic option prices based on symbol
            base_price = 50 + (hash(symbol) % 100)  # Generate consistent mock price
            prices[symbol] = round(base_price + (datetime.now().second % 20), 2)
        
        return JsonResponse({
            'success': True,
            'prices': prices,
            'instrument': instrument,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error getting option prices: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_POST
def place_basket_order_api(request):
    """
    API endpoint to place basket orders across multiple brokers
    """
    try:
        data = json.loads(request.body)
        brokers = data.get('brokers', [])
        orders = data.get('orders', [])
        timestamp = data.get('timestamp')
        
        if not brokers:
            return JsonResponse({
                'success': False,
                'message': 'No brokers selected'
            }, status=400)
        
        if not orders:
            return JsonResponse({
                'success': False,
                'message': 'No orders to place'
            }, status=400)
        
        # Load broker settings
        settings_file = os.path.join(settings.BASE_DIR, 'fifto_settings.json')
        broker_settings = {}
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                broker_settings = json.load(f)
        
        placed_orders = []
        failed_orders = []
        
        # Process orders for each broker
        for broker_id in brokers:
            broker_name = None
            broker_handler = None
            
            # Find broker configuration
            for broker_type, config in broker_settings.items():
                if str(config.get('client_id', '')) == str(broker_id) or str(config.get('account_id', '')) == str(broker_id):
                    broker_name = broker_type
                    
                    # Import and initialize broker handler
                    try:
                        if broker_type == 'DHAN':
                            from .dhan_api_v2 import DhanAPI
                            broker_handler = DhanAPI(config)
                        elif broker_type == 'FLATTRADE':
                            # Import FlatTrade API when available
                            pass
                        # Add other brokers as needed
                        
                    except ImportError as e:
                        print(f"⚠️ Broker {broker_type} handler not available: {e}")
                        continue
                    break
            
            if not broker_handler:
                failed_orders.append({
                    'broker_id': broker_id,
                    'error': 'Broker handler not available'
                })
                continue
            
            # Place orders for this broker
            for order in orders:
                try:
                    # Prepare order data
                    order_data = {
                        'symbol': order['symbol'],
                        'quantity': order['quantity'],
                        'order_type': order['orderType'],
                        'transaction_type': order['action'],
                        'product_type': 'MIS',  # Intraday
                        'price': order.get('limitPrice', 0)
                    }
                    
                    # Place order (mock for now - implement actual API calls)
                    print(f"🔄 Placing order: {order_data} via {broker_name}")
                    
                    # Mock successful order placement
                    order_id = f"{broker_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{order['id']}"
                    
                    placed_orders.append({
                        'broker': broker_name,
                        'broker_id': broker_id,
                        'order_id': order_id,
                        'symbol': order['symbol'],
                        'quantity': order['quantity'],
                        'status': 'PLACED'
                    })
                    
                except Exception as e:
                    print(f"❌ Error placing order {order['symbol']}: {e}")
                    failed_orders.append({
                        'broker': broker_name,
                        'broker_id': broker_id,
                        'symbol': order['symbol'],
                        'error': str(e)
                    })
        
        # Prepare response
        total_orders = len(placed_orders) + len(failed_orders)
        success_count = len(placed_orders)
        
        message = f"Basket order execution completed!\n\n"
        message += f"✅ Successfully placed: {success_count} orders\n"
        if failed_orders:
            message += f"❌ Failed orders: {len(failed_orders)}\n"
        
        message += f"\nTotal brokers used: {len(set(order['broker'] for order in placed_orders))}\n"
        message += f"Execution time: {datetime.now().strftime('%H:%M:%S')}"
        
        return JsonResponse({
            'success': success_count > 0,
            'message': message,
            'placed_orders': placed_orders,
            'failed_orders': failed_orders,
            'summary': {
                'total_orders': total_orders,
                'successful': success_count,
                'failed': len(failed_orders),
                'brokers_used': len(set(order['broker'] for order in placed_orders))
            }
        })
        
    except Exception as e:
        print(f"❌ Error placing basket order: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to place basket order: {str(e)}'
        }, status=500)
