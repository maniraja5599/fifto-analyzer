# analyzer/views.py - Clean New Implementation

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.conf import settings
import json
import pandas as pd
import os
from datetime import datetime
from collections import defaultdict
from . import utils
from .utils import load_settings, save_settings
from .pnl_updater import pnl_updater, PnLUpdater

def parse_start_time(start_time_str):
    """Parse start_time in either old (24-hour) or new (12-hour) format."""
    try:
        # Try new format first (12-hour with AM/PM)
        return datetime.strptime(start_time_str, "%Y-%m-%d %I:%M %p")
    except ValueError:
        try:
            # Fall back to old format (24-hour)
            return datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            # If neither works, return current time as fallback
            return datetime.now()

def index(request):
    # Handle session clearing
    if request.method == 'POST' and request.POST.get('clear_session'):
        request.session.pop('analysis_data', None)
        return JsonResponse({'status': 'cleared'})
    
    analysis_data = request.session.get('analysis_data')
    instrument = request.GET.get('instrument', 'NIFTY')
    
    # Get option chain data with improved error handling
    chain_expiries = utils.get_option_chain_expiry_dates_only(instrument)
    expiries = []
    
    try:
        if chain_expiries:
            all_expiries = chain_expiries
            # Filter future dates only
            from datetime import datetime as dt, timedelta
            current_date = dt.now().date()
            expiries = []
            
            for expiry_str in all_expiries:
                try:
                    expiry_date = dt.strptime(expiry_str, "%Y-%m-%d").date()
                    if expiry_date >= current_date:
                        expiries.append(expiry_date.strftime("%d-%b-%Y"))
                except ValueError:
                    # Try alternative format
                    try:
                        expiry_date = dt.strptime(expiry_str, "%d-%b-%Y").date()
                        if expiry_date >= current_date:
                            expiries.append(expiry_str)
                    except ValueError:
                        continue
                    
            # Sort by date
            expiries.sort(key=lambda x: dt.strptime(x, "%d-%b-%Y"))
            print(f"✅ Loaded {len(expiries)} expiry dates for {instrument}: {expiries[:3]}...")
        else:
            print(f"⚠️ No expiry dates found for {instrument}, using fallback")
            
    except Exception as e:
        print(f"❌ Error processing expiry dates: {e}")
        
    # Ensure we have at least some expiries (fallback)
    if not expiries:
        from datetime import datetime as dt, timedelta
        print(f"🔄 Generating fallback expiry dates for {instrument}")
        base_date = dt.now().date()
        for i in range(1, 5):  # Next 4 weeks
            fallback_date = base_date + timedelta(weeks=i)
            # Adjust to Thursday (weekday 3)
            days_to_add = (3 - fallback_date.weekday()) % 7
            thursday = fallback_date + timedelta(days=days_to_add)
            expiries.append(thursday.strftime("%d-%b-%Y"))
            
    context = {
        'expiries': expiries,
        'instrument': instrument,
        'analysis_data': analysis_data,
        'expiry_count': len(expiries)
    }
    return render(request, 'analyzer/index.html', context)

def generate_and_show_analysis(request):
    # Create a debug log file
    debug_file = r"C:\Users\manir\Desktop\debug_log.txt"
    
    def debug_log(message):
        with open(debug_file, 'a', encoding='utf-8') as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            f.write(f"[{timestamp}] {message}\n")
        print(message)  # Also print to console
    
    debug_log("=== Generate Analysis View Called ===")
    debug_log(f"Request method: {request.method}")
    
    if request.method == 'POST':
        instrument = request.POST.get('instrument')
        calc_type = request.POST.get('calc_type')
        expiry = request.POST.get('expiry')
        coefficient = float(request.POST.get('coefficient', 85)) / 100  # Convert percentage to decimal
        hedge_percentage = float(request.POST.get('hedge_percentage', 10))  # Default 10% hedge
        risk_levels = request.POST.getlist('risk_levels')  # Get multiple risk levels
        
        # Default to high risk if none selected
        if not risk_levels:
            risk_levels = ['high']
        
        debug_log(f"Form data received:")
        debug_log(f"  Instrument: {instrument}")
        debug_log(f"  Calculation Type: {calc_type}")
        debug_log(f"  Expiry: {expiry}")
        debug_log(f"  Coefficient: {coefficient}")
        debug_log(f"  Hedge Percentage: {hedge_percentage}%")
        debug_log(f"  Risk Levels: {risk_levels}")
        
        try:
            debug_log("Calling generate_multi_risk_analysis()...")
            
            # Generate analysis for each selected risk level
            combined_analysis_data = utils.generate_multi_risk_analysis(
                instrument, calc_type, expiry, risk_levels, hedge_percentage
            )
            
            if combined_analysis_data:
                request.session['analysis_data'] = combined_analysis_data
                strategy_count = len(combined_analysis_data['df_data'])
                risk_names = [r.upper() for r in risk_levels]
                success_msg = f"✅ Generated {strategy_count} strategies for {', '.join(risk_names)} risk levels"
                messages.success(request, success_msg)
                debug_log("✅ Analysis successful - data saved to session")
            else:
                messages.error(request, "Failed to generate analysis")
                debug_log("❌ Analysis failed")
        except Exception as e:
            error_msg = f"Error generating analysis: {str(e)}"
            messages.error(request, error_msg)
            debug_log(f"❌ Exception occurred: {error_msg}")
            import traceback
            debug_log(f"Traceback: {traceback.format_exc()}")
        
        return redirect(reverse('index'))
    
    debug_log("❌ Non-POST request - redirecting to index")
    return redirect(reverse('index'))

@require_http_methods(["POST"])
def place_live_orders(request):
    """API endpoint for manual live order placement"""
    try:
        # Check if live trading is enabled
        current_settings = utils.load_settings()
        if not current_settings.get('enable_live_trading', False):
            return JsonResponse({
                'success': False,
                'message': 'Live trading is not enabled in settings'
            })
        
        # Get analysis data from session
        analysis_data = request.session.get('analysis_data')
        if not analysis_data:
            return JsonResponse({
                'success': False,
                'message': 'No analysis data found. Please generate an analysis first.'
            })
        
        # Import broker manager
        from .broker_manager import broker_manager
        
        # Get enabled broker accounts
        enabled_accounts = []
        for acc in current_settings.get('broker_accounts', []):
            if acc.get('enabled', False):
                # For FlatTrade, use client_id; for others, use account_id
                account_id = acc.get('client_id') if acc.get('broker') == 'FLATTRADE' else acc.get('account_id')
                if account_id:
                    enabled_accounts.append(account_id)
        
        if not enabled_accounts:
            return JsonResponse({
                'success': False,
                'message': 'No enabled broker accounts found. Please configure broker accounts in settings.'
            })
        
        # Place orders
        live_trading_result = broker_manager.place_strategy_orders(
            analysis_data, 
            account_ids=enabled_accounts
        )
        
        if live_trading_result['success']:
            orders_count = len(live_trading_result['orders_placed'])
            accounts_count = live_trading_result['successful_accounts']
            
            # Send Telegram notification
            if current_settings.get('enable_trade_alerts', False):
                telegram_msg = f"📱 **Manual Live Orders**\n\n"
                telegram_msg += f"📊 Strategy: {analysis_data.get('instrument')} {analysis_data.get('expiry')}\n"
                telegram_msg += f"📈 Orders: {orders_count} placed\n"
                telegram_msg += f"🏦 Accounts: {accounts_count} brokers\n"
                telegram_msg += f"👤 Triggered: Manually\n"
                telegram_msg += f"⏰ Time: {datetime.now().strftime('%I:%M:%S %p')}"
                utils.send_telegram_message(telegram_msg)
            
            # Start position monitoring if enabled (either global or schedule-based)
            if current_settings.get('enable_position_monitoring', False):
                from .position_monitor import position_monitor
                
                # Get the latest trades that were just added
                trades = utils.load_trades()
                instrument = analysis_data.get('instrument')
                latest_trades = [t for t in trades if t.get('instrument') == instrument]
                
                # Check if there's any automation schedule with trade close enabled for this instrument
                schedule_config = None
                multiple_schedules = current_settings.get('multiple_schedules', [])
                for schedule in multiple_schedules:
                    if (schedule.get('enabled') and 
                        schedule.get('enable_trade_close') and 
                        instrument in schedule.get('instruments', [])):
                        schedule_config = schedule
                        break
                
                # Add positions to monitoring
                for trade in latest_trades[-len(analysis_data.get('df_data', [])):]:  # Get latest trades
                    if schedule_config:
                        # Use schedule configuration for trade close settings
                        position_monitor.add_position_for_monitoring(
                            trade, 
                            live_trading_result['orders_placed'],
                            schedule_config
                        )
                    else:
                        # Use default/trade-based settings
                        position_monitor.add_position_for_monitoring(
                            trade, 
                            live_trading_result['orders_placed']
                        )
                
                # Start monitoring service if not already running
                if not position_monitor.running:
                    position_monitor.start_monitoring()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully placed {orders_count} orders across {accounts_count} broker accounts',
                'orders_count': orders_count,
                'accounts_count': accounts_count,
                'orders': live_trading_result['orders_placed']
            })
        else:
            error_msg = '; '.join(live_trading_result['errors'][:3])  # Show first 3 errors
            return JsonResponse({
                'success': False,
                'message': f'Order placement failed: {error_msg}',
                'errors': live_trading_result['errors']
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Live trading error: {str(e)}'
        })

def check_task_status(request, task_id):
    """Simple status check - not needed for basic version."""
    return JsonResponse({
        'success': True,
        'completed': True,
        'message': 'Task completed'
    })

def add_trades(request):
    """
    Add analysis results to active trades portfolio
    """
    print("🚀 ADD_TRADES FUNCTION CALLED!")
    
    analysis_data = request.session.get('analysis_data')
    print(f"📊 Analysis data found: {analysis_data is not None}")
    
    if analysis_data:
        print(f"📈 Analysis data keys: {list(analysis_data.keys())}")
        print(f"📊 Instrument: {analysis_data.get('instrument', 'Not found')}")
        print(f"📅 Expiry: {analysis_data.get('expiry', 'Not found')}")
        print(f"📋 df_data length: {len(analysis_data.get('df_data', []))}")
        if analysis_data.get('df_data'):
            print(f"📝 Sample df_data entry: {analysis_data['df_data'][0] if analysis_data['df_data'] else 'Empty'}")
    
    if not analysis_data:
        print("⚠️ No analysis data found in session")
        messages.warning(request, 'Please generate an analysis first before adding to portfolio.')
        return redirect(reverse('index'))
    
    print(f"📈 Processing analysis for {analysis_data.get('instrument', 'Unknown')} {analysis_data.get('expiry', 'Unknown')}")
    
    # Check live trading settings
    current_settings = utils.load_settings()
    enable_live_trading = current_settings.get('enable_live_trading', False)
    auto_place_orders = current_settings.get('auto_place_orders', False)
    
    # Live trading integration
    live_trading_result = None
    if enable_live_trading and auto_place_orders:
        try:
            from .broker_manager import broker_manager
            
            print("🔄 Live trading enabled - placing orders automatically...")
            
            # Get enabled broker accounts
            enabled_accounts = []
            for acc in current_settings.get('broker_accounts', []):
                if acc.get('enabled', False):
                    # For FlatTrade, use client_id; for others, use account_id
                    account_id = acc.get('client_id') if acc.get('broker') == 'FLATTRADE' else acc.get('account_id')
                    if account_id:
                        enabled_accounts.append(account_id)
            
            if enabled_accounts:
                live_trading_result = broker_manager.place_strategy_orders(
                    analysis_data, 
                    account_ids=enabled_accounts
                )
                
                if live_trading_result['success']:
                    orders_count = len(live_trading_result['orders_placed'])
                    accounts_count = live_trading_result['successful_accounts']
                    messages.success(request, 
                        f'🚀 Live Trading: {orders_count} orders placed across {accounts_count} broker accounts!')
                    
                    # Send Telegram notification about live orders
                    if current_settings.get('enable_trade_alerts', False):
                        telegram_msg = f"🚀 **Live Orders Placed**\n\n"
                        telegram_msg += f"📊 Strategy: {analysis_data.get('instrument')} {analysis_data.get('expiry')}\n"
                        telegram_msg += f"📈 Orders: {orders_count} placed\n"
                        telegram_msg += f"🏦 Accounts: {accounts_count} brokers\n"
                        telegram_msg += f"⏰ Time: {datetime.now().strftime('%I:%M:%S %p')}"
                        utils.send_telegram_message(telegram_msg)
                else:
                    error_msg = '; '.join(live_trading_result['errors'][:3])  # Show first 3 errors
                    messages.warning(request, f'⚠️ Live Trading Issues: {error_msg}')
            else:
                messages.info(request, '📝 Live trading enabled but no broker accounts configured')
                
        except Exception as e:
            print(f"❌ Live trading error: {e}")
            messages.error(request, f'❌ Live trading error: {str(e)}')
    
    # Check trades before adding
    trades_before = utils.load_trades()
    print(f"📊 Trades before adding: {len(trades_before)}")
    
    # Show existing trade IDs to check for duplicates
    if trades_before:
        print("🔍 Existing trade IDs:")
        for trade in trades_before:
            print(f"   - {trade.get('id', 'NO_ID')}")
    
    try:
        status = utils.add_to_analysis(analysis_data)
        print(f"📝 Add to analysis result: {status}")
        
        # Check trades after adding
        trades_after = utils.load_trades()
        print(f"📈 Trades after adding: {len(trades_after)}")
        
        if len(trades_after) > len(trades_before):
            print("✅ New trades were added successfully!")
            new_trades = trades_after[len(trades_before):]
            for trade in new_trades:
                print(f"   🔹 Added: {trade['id']} | Status: {trade['status']} | Tag: {trade['entry_tag']}")
            
            # Clear the analysis data from session since trades have been added successfully
            if 'analysis_data' in request.session:
                del request.session['analysis_data']
                print("🗑️ Cleared analysis data from session")
            
            messages.success(request, f"✅ {status}")
        else:
            print("ℹ️ No new trades added (duplicates prevented)")
            messages.info(request, f"ℹ️ {status}")
            
    except Exception as e:
        error_msg = f"Error adding trades: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        messages.error(request, error_msg)
    
    print("🔄 Redirecting to trades_list")
    return redirect(reverse('trades_list'))


    trades = utils.load_trades()
    df = pd.DataFrame(trades) if trades else pd.DataFrame()
    if not df.empty:
        df['lot_size'] = df['instrument'].apply(lambda x: utils.get_lot_size(x))
        df['initial_amount'] = (df['initial_premium'] * df['lot_size']).round(2)
        df = df[['id', 'entry_tag', 'start_time', 'status', 'initial_amount', 'target_amount', 'stoploss_amount']]
        df.rename(columns={'id': 'ID', 'entry_tag': 'Tag', 'start_time': 'Start Time', 'status': 'Status', 'initial_amount': 'Initial Amount (₹)', 'target_amount': 'Target Profit (₹)', 'stoploss_amount': 'Stoploss (₹)'}, inplace=True)
        df_html = df.to_html(classes='table table-striped', index=False, justify='center', render_links=True, escape=False)
        df_html = df_html.replace('<td>', '<td style="text-align: center;">')
        df_html = df_html.replace('<th>', '<th style="text-align: center;">')
    else:
        df_html = ""
    return render(request, 'analyzer/trades.html', {'trades_html': df_html})

def check_and_auto_close_trades(trades):
    """
    Check all running trades for target/stoploss conditions and auto-close them
    Returns list of auto-closed trade IDs
    Note: Only works when fresh market data is available (after manual refresh)
    """
    auto_closed = []
    
    # Skip auto-close monitoring if no market data is available
    # This prevents unnecessary API calls - auto-close only works after manual refresh
    try:
        # Check if we have cached market data from recent manual refresh
        cache_file = os.path.join(settings.BASE_DIR, 'market_data_cache.json')
        if not os.path.exists(cache_file):
            print("📝 Auto-close skipped: No market data cache available (manual refresh required)")
            return auto_closed
            
        # Only fetch market data if we have a recent cache (within last 5 minutes)
        import time
        cache_age = time.time() - os.path.getctime(cache_file)
        if cache_age > 300:  # 5 minutes
            print("📝 Auto-close skipped: Market data cache too old (manual refresh required)")
            return auto_closed
            
        # Get current market data only if cache is fresh
        nifty_chain = utils.get_option_chain_data("NIFTY")
        banknifty_chain = utils.get_option_chain_data("BANKNIFTY")
        
    except Exception as e:
        print(f"📝 Auto-close skipped: Error accessing market data - {e}")
        return auto_closed
    
    for trade in trades:
        if trade.get('status') != 'Running':
            continue
            
        # Skip if trade doesn't have target/stoploss defined
        target_amount = trade.get('target_amount')
        stoploss_amount = trade.get('stoploss_amount')
        
        if not target_amount and not stoploss_amount:
            continue
            
        # Calculate current P&L
        current_pnl = 0
        try:
            # Use appropriate chain data based on instrument
            chain_data = nifty_chain if trade.get('instrument') == 'NIFTY' else banknifty_chain
            
            if chain_data:
                current_ce, current_pe = 0.0, 0.0
                
                # Handle NSE data structure only
                records = chain_data.get('records', {})
                if records and 'data' in records and isinstance(records['data'], list):
                    for item in records['data']:
                        if item.get("expiryDate") == trade.get('expiry'):
                            if item.get("strikePrice") == trade.get('ce_strike') and item.get("CE"):
                                current_ce = item["CE"]["lastPrice"]
                            if item.get("strikePrice") == trade.get('pe_strike') and item.get("PE"):
                                current_pe = item["PE"]["lastPrice"]
                
                # Calculate P&L using current market prices
                lot_size = utils.get_lot_size(trade['instrument'])
                initial_premium = trade.get('initial_premium', 0)
                current_premium = current_ce + current_pe
                
                if current_premium > 0:
                    current_pnl = round((initial_premium - current_premium) * lot_size, 2)
                else:
                    current_pnl = trade.get('pnl', 0)
            else:
                current_pnl = trade.get('pnl', 0)
                
        except Exception as e:
            print(f"Error calculating P&L for auto-close trade {trade.get('id')}: {e}")
            current_pnl = trade.get('pnl', 0)
        
        # Check target condition
        should_close = False
        close_reason = ""
        
        if target_amount and current_pnl >= float(target_amount):
            should_close = True
            close_reason = "Target Hit"
            
        # Check stoploss condition
        elif stoploss_amount and current_pnl <= -float(stoploss_amount):
            should_close = True
            close_reason = "Stoploss Hit"
        
        # Auto-close the trade if conditions are met
        if should_close:
            trade['status'] = f'Auto Closed - {close_reason}'
            trade['final_pnl'] = current_pnl
            trade['closed_date'] = datetime.now().isoformat()
            auto_closed.append(trade['id'])
            
            # Send Telegram notification
            utils.send_telegram_message(f"🤖 Auto Close: Trade {trade['id']} closed due to {close_reason} with P&L ₹{current_pnl:.2f}")
    
    # Save trades if any were auto-closed
    if auto_closed:
        utils.save_trades(trades)
        
    return auto_closed

# In analyzer/views.py

# analyzer/views.py

# In analyzer/views.py

def trades_list(request):
    trades = utils.load_trades()
    
    # Auto-close trades that hit target or stoploss before displaying
    auto_closed_trades = check_and_auto_close_trades(trades)
    if auto_closed_trades:
        trades = utils.load_trades()  # Reload trades after auto-close updates
    
    # Load current settings to get last used group_by preference
    current_settings = utils.load_settings()
    
    # Get filter parameters with persistence for group_by
    group_by = request.GET.get('group_by')
    if group_by:
        # Save the group_by preference when user explicitly changes it
        current_settings['last_group_by'] = group_by
        utils.save_settings(current_settings)
    else:
        # Use the last saved preference, default to 'expiry'
        group_by = current_settings.get('last_group_by', 'expiry')
    
    instrument_filter = request.GET.get('instrument', 'all')
    tag_filter = request.GET.get('tag', 'all')
    
    # Handle trade operations (delete, bulk delete, close trades)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete_trade':
            trade_id = request.POST.get('trade_id')
            trades = [t for t in trades if t['id'] != trade_id]
            utils.save_trades(trades)
            # Send Telegram notification
            utils.send_telegram_message(f"🗑️ Trade Deleted: {trade_id}")
            messages.success(request, f'Trade {trade_id} deleted successfully.')
            return redirect('trades_list')
            
        elif action == 'close_trade':
            trade_id = request.POST.get('trade_id')
            
            # Use last known P&L instead of fetching fresh data (optimization)
            closed_count = 0
            current_pnl = 0
            trade_broker_accounts = []
            
            for trade in trades:
                if trade['id'] == trade_id:
                    # Get broker accounts associated with this trade
                    trade_broker_accounts = trade.get('broker_accounts', [])
                    
                    # Use the last calculated P&L (from last manual refresh)
                    current_pnl = trade.get('pnl', 0)
                    if current_pnl == "Refresh Required":
                        current_pnl = 0  # Default to 0 if no fresh data
                    elif isinstance(current_pnl, str):
                        try:
                            current_pnl = float(current_pnl)
                        except (ValueError, TypeError):
                            current_pnl = 0
                    
                    # If this trade has broker accounts and live trading was enabled, attempt broker closing
                    if trade_broker_accounts and trade.get('live_trading_enabled', False):
                        try:
                            from .broker_manager import broker_manager
                            
                            # Close positions for specific broker accounts associated with this trade
                            close_result = broker_manager.close_trade_positions(trade, trade_broker_accounts)
                            
                            if close_result.get('success', False):
                                # Add broker closing info to trade
                                trade['broker_close_result'] = close_result
                                trade['closed_via_broker'] = True
                                messages.success(request, f'✅ Trade {trade_id} closed via live broker(s): {", ".join(trade_broker_accounts)}')
                            else:
                                messages.warning(request, f'⚠️ Partial broker close for {trade_id}. Manual verification recommended.')
                                
                        except Exception as e:
                            messages.warning(request, f'⚠️ Could not close broker positions: {str(e)}. Trade marked as manually closed.')
                    
                    # Close the trade with last known P&L
                    trade['status'] = 'Manually Closed'
                    trade['final_pnl'] = current_pnl
                    trade['closed_date'] = datetime.now().isoformat()
                    closed_count += 1
                    break
                    
            utils.save_trades(trades)
            
            # Send Telegram notification with broker info
            broker_info = f" (Brokers: {', '.join(trade_broker_accounts)})" if trade_broker_accounts else ""
            utils.send_telegram_message(f"📝 Manual Close: Trade {trade_id}{broker_info} closed with P&L ₹{current_pnl:.2f}")
            messages.success(request, f'Trade {trade_id} closed with P&L ₹{current_pnl:.2f}.')
            return redirect('trades_list')
            
        elif action == 'delete_multiple':
            # Handle both parameter names for backward compatibility
            trade_ids = request.POST.getlist('selected_trades')
            if not trade_ids:
                # Try the alternate parameter name
                trade_ids_str = request.POST.get('trade_ids', '')
                trade_ids = [tid.strip() for tid in trade_ids_str.split(',') if tid.strip()]
            
            original_count = len(trades)
            trades = [t for t in trades if t['id'] not in trade_ids]
            deleted_count = original_count - len(trades)
            utils.save_trades(trades)
            # Send Telegram notification
            utils.send_telegram_message(f"🗑️ Bulk Delete: {deleted_count} trades deleted")
            messages.success(request, f'Deleted {deleted_count} trades successfully.')
            return redirect('trades_list')
            
        elif action == 'close_multiple':
            # Handle both parameter names for backward compatibility
            trade_ids = request.POST.getlist('selected_trades')
            if not trade_ids:
                # Try the alternate parameter name
                trade_ids_str = request.POST.get('trade_ids', '')
                trade_ids = [tid.strip() for tid in trade_ids_str.split(',') if tid.strip()]
            
            closed_count = 0
            total_pnl = 0
            for trade in trades:
                if trade['id'] in trade_ids:
                    # Calculate real P&L using current market data
                    try:
                        if trade.get('symbol') and trade.get('strike') and trade.get('option_type'):
                            symbol = trade['symbol'].replace(' ', '%20')  # URL encode spaces
                            market_data = utils.get_option_chain_data(symbol)
                            
                            if market_data:
                                option_data = next((item for item in market_data 
                                                  if str(item.get('strike_price', '')) == str(trade['strike']) 
                                                  and item.get('option_type', '').upper() == trade['option_type'].upper()), None)
                                
                                if option_data:
                                    current_ltp = float(option_data.get('ltp', 0))
                                    entry_premium = float(trade.get('entry_premium', 0))
                                    quantity = int(trade.get('quantity', 0))
                                    lot_size = utils.get_lot_size(trade['symbol'])
                                    total_quantity = quantity * lot_size
                                    
                                    if trade.get('trade_type', '').upper() == 'BUY':
                                        current_pnl = (current_ltp - entry_premium) * total_quantity
                                    else:  # SELL
                                        current_pnl = (entry_premium - current_ltp) * total_quantity
                                else:
                                    current_pnl = trade.get('pnl', 0)
                            else:
                                current_pnl = trade.get('pnl', 0)
                        else:
                            current_pnl = trade.get('pnl', 0)
                    except Exception as e:
                        print(f"Error calculating P&L for trade {trade.get('id')}: {e}")
                        current_pnl = trade.get('pnl', 0)
                    
                    trade['status'] = 'Manually Closed'
                    trade['final_pnl'] = current_pnl
                    trade['closed_date'] = datetime.now().isoformat()
                    total_pnl += current_pnl
                    closed_count += 1
            utils.save_trades(trades)
            # Send Telegram notification
            utils.send_telegram_message(f"📝 Manual Close: {closed_count} trades closed with total P&L ₹{total_pnl:.2f}")
            messages.success(request, f'Closed {closed_count} trades successfully with total P&L ₹{total_pnl:.2f}.')
            return redirect('trades_list')
            
        elif action == 'close_group':
            closed_count = 0
            total_pnl = 0
            if group_by == 'automation_batch':
                batch_tag = request.POST.get('batch_tag')
                for trade in trades:
                    if trade.get('entry_tag', 'General Trades') == batch_tag and trade.get('status') == 'Running':
                        current_pnl = trade.get('pnl', 0)
                        trade['status'] = 'Manually Closed'
                        trade['final_pnl'] = current_pnl
                        trade['closed_date'] = datetime.now().isoformat()
                        total_pnl += current_pnl
                        closed_count += 1
                utils.save_trades(trades)
                # Send Telegram notification
                utils.send_telegram_message(f"📝 Automation Batch Close: {closed_count} trades from '{batch_tag}' closed with total P&L ₹{total_pnl:.2f}")
                messages.success(request, f'Closed {closed_count} trades from automation batch "{batch_tag}" with total P&L ₹{total_pnl:.2f}.')
            elif group_by == 'day':
                day_group = request.POST.get('day_group')
                for trade in trades:
                    try:
                        start_dt = parse_start_time(trade['start_time'])
                        trade_day = start_dt.strftime('%d-%b-%Y')
                        if trade_day == day_group and trade.get('status') == 'Running':
                            current_pnl = trade.get('pnl', 0)
                            trade['status'] = 'Manually Closed'
                            trade['final_pnl'] = current_pnl
                            trade['closed_date'] = datetime.now().isoformat()
                            total_pnl += current_pnl
                            closed_count += 1
                    except (ValueError, KeyError):
                        continue
                utils.save_trades(trades)
                # Send Telegram notification
                utils.send_telegram_message(f"📝 Day Close: {closed_count} trades from '{day_group}' closed with total P&L ₹{total_pnl:.2f}")
                messages.success(request, f'Closed {closed_count} trades from day "{day_group}" with total P&L ₹{total_pnl:.2f}.')
            else:  # expiry grouping
                expiry_date = request.POST.get('expiry_date')
                for trade in trades:
                    if trade.get('expiry') == expiry_date and trade.get('status') == 'Running':
                        current_pnl = trade.get('pnl', 0)
                        trade['status'] = 'Manually Closed'
                        trade['final_pnl'] = current_pnl
                        trade['closed_date'] = datetime.now().isoformat()
                        total_pnl += current_pnl
                        closed_count += 1
                utils.save_trades(trades)
                # Send Telegram notification
                utils.send_telegram_message(f"📝 Expiry Close: {closed_count} trades expiring on '{expiry_date}' closed with total P&L ₹{total_pnl:.2f}")
                messages.success(request, f'Closed {closed_count} trades expiring on "{expiry_date}" with total P&L ₹{total_pnl:.2f}.')
            return redirect('trades_list')
            
        elif action == 'delete_batch':
            if group_by == 'automation_batch':
                batch_tag = request.POST.get('batch_tag')
                original_count = len(trades)
                trades = [t for t in trades if t.get('entry_tag', 'General Trades') != batch_tag]
                deleted_count = original_count - len(trades)
                utils.save_trades(trades)
                # Send Telegram notification
                utils.send_telegram_message(f"🗑️ Automation Batch Delete: {deleted_count} trades from '{batch_tag}' deleted")
                messages.success(request, f'Deleted {deleted_count} trades from automation batch "{batch_tag}".')
            elif group_by == 'day':
                day_group = request.POST.get('day_group')
                original_count = len(trades)
                filtered_trades = []
                for trade in trades:
                    try:
                        start_dt = parse_start_time(trade['start_time'])
                        trade_day = start_dt.strftime('%d-%b-%Y')
                        if trade_day != day_group:
                            filtered_trades.append(trade)
                    except (ValueError, KeyError):
                        filtered_trades.append(trade)
                trades = filtered_trades
                deleted_count = original_count - len(trades)
                utils.save_trades(trades)
                # Send Telegram notification
                utils.send_telegram_message(f"🗑️ Day Delete: {deleted_count} trades from '{day_group}' deleted")
                messages.success(request, f'Deleted {deleted_count} trades from day "{day_group}".')
            else:  # expiry grouping
                expiry_date = request.POST.get('expiry_date')
                original_count = len(trades)
                trades = [t for t in trades if t.get('expiry') != expiry_date]
                deleted_count = original_count - len(trades)
                utils.save_trades(trades)
                # Send Telegram notification
                utils.send_telegram_message(f"🗑️ Expiry Delete: {deleted_count} trades expiring on '{expiry_date}' deleted")
                messages.success(request, f'Deleted {deleted_count} trades expiring on "{expiry_date}".')
            return redirect('trades_list')
            
        elif action == 'update_target_stoploss':
            trade_id = request.POST.get('trade_id')
            target_amount = request.POST.get('target_amount')
            stoploss_amount = request.POST.get('stoploss_amount')
            
            try:
                target_amount = float(target_amount) if target_amount else 0
                stoploss_amount = float(stoploss_amount) if stoploss_amount else 0
                
                if target_amount <= 0 or stoploss_amount <= 0:
                    return JsonResponse({'success': False, 'message': 'Target and stoploss amounts must be greater than 0'})
                
                # Find and update the trade
                trade_found = False
                for trade in trades:
                    if trade['id'] == trade_id:
                        trade['target_amount'] = target_amount
                        trade['stoploss_amount'] = stoploss_amount
                        trade_found = True
                        break
                
                if not trade_found:
                    return JsonResponse({'success': False, 'message': 'Trade not found'})
                
                # Save updated trades
                utils.save_trades(trades)
                
                # Send Telegram notification
                utils.send_telegram_message(f"📝 Target/SL Updated: {trade_id} - Target: ₹{target_amount:.2f}, SL: ₹{stoploss_amount:.2f}")
                
                return JsonResponse({
                    'success': True, 
                    'message': 'Target and stoploss updated successfully',
                    'target_amount': target_amount,
                    'stoploss_amount': stoploss_amount
                })
                
            except (ValueError, TypeError) as e:
                return JsonResponse({'success': False, 'message': 'Invalid target or stoploss amount'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Error updating trade: {str(e)}'})

    # Filter trades by instrument
    if instrument_filter != 'all':
        trades = [t for t in trades if t.get('instrument') == instrument_filter]
    
    # Filter trades by tag
    if tag_filter != 'all':
        trades = [t for t in trades if t.get('entry_tag') == tag_filter]

    # Separate active and closed trades
    active_trades = [t for t in trades if t.get('status') == 'Running']
    closed_trades = [t for t in trades if t.get('status') in ['Target', 'Stoploss', 'Manually Closed']]

    # Group active trades and calculate P&L
    grouped_trades = defaultdict(list)
    total_pnl = 0
    
    # Initialize market data as None - will be fetched only on manual refresh
    nifty_chain = None
    banknifty_chain = None
    
    # Note: Option chain data is now fetched only on manual refresh to optimize performance
    # Current premium and P&L will show "Refresh Required" until manual refresh is triggered

    for trade in active_trades:
        try:
            # Parse and format the date tag
            start_dt = parse_start_time(trade['start_time'])
            display_tag = f"{start_dt.strftime('%d-%b')} {trade.get('entry_tag', '')}"
            trade['display_tag'] = display_tag
        except (ValueError, KeyError):
            trade['display_tag'] = trade.get('entry_tag', 'General Trades')

        # Calculate current P&L - only if market data is available
        chain_data = nifty_chain if trade['instrument'] == 'NIFTY' else banknifty_chain
        current_ce, current_pe = 0.0, 0.0
        
        if chain_data is not None:
            # Handle NSE data structure only
            records = chain_data.get('records', {})
            if records and 'data' in records and isinstance(records['data'], list):
                for item in records['data']:
                    if item.get("expiryDate") == trade.get('expiry'):
                        if item.get("strikePrice") == trade.get('ce_strike') and item.get("CE"):
                            current_ce = item["CE"]["lastPrice"]
                        if item.get("strikePrice") == trade.get('pe_strike') and item.get("PE"):
                            current_pe = item["PE"]["lastPrice"]
        
        lot_size = utils.get_lot_size(trade['instrument'])
        initial_premium = trade.get('initial_premium', 0)
        current_premium = current_ce + current_pe
        
        if current_premium > 0 and chain_data is not None:
            # We have fresh market data, calculate actual P&L
            pnl = round((initial_premium - current_premium) * lot_size, 2)
            trade['pnl'] = pnl
            trade['current_premium'] = current_premium
            total_pnl += pnl
            
            # Check for target/stoploss and send alerts (only when we have fresh data)
            target_amount = trade.get('target_amount', 0)
            stoploss_amount = trade.get('stoploss_amount', 0)
            
            if pnl >= target_amount and target_amount > 0:
                trade['status'] = 'Target'
                utils.save_trades(trades)
                # Send Telegram alert
                utils.send_telegram_message(f"🎯 TARGET HIT!\nTrade: {trade['id']}\nP&L: ₹{pnl:,.2f}")
                messages.success(request, f"Target hit for {trade['id']}! P&L: ₹{pnl:,.2f}")
            elif pnl <= -stoploss_amount and stoploss_amount > 0:
                trade['status'] = 'Stoploss'
                utils.save_trades(trades)
                # Send Telegram alert
                utils.send_telegram_message(f"🛑 STOPLOSS HIT!\nTrade: {trade['id']}\nP&L: ₹{pnl:,.2f}")
                messages.error(request, f"Stoploss hit for {trade['id']}! P&L: ₹{pnl:,.2f}")
        else:
            # No fresh market data available, show placeholder
            trade['pnl'] = "Refresh Required"
            trade['current_premium'] = "Refresh Required"
        
        # Group by automation_batch, day, or expiry
        if group_by == 'automation_batch':
            # Group by automation generation (one automation creates one batch)
            group_key = trade.get('entry_tag', 'General Trades')
        elif group_by == 'day':
            # Group by day
            try:
                start_dt = parse_start_time(trade['start_time'])
                group_key = start_dt.strftime('%d-%b-%Y')
            except (ValueError, KeyError):
                group_key = 'Unknown Date'
        else:  # expiry grouping
            group_key = trade.get('expiry', 'Unknown Expiry')
        
        grouped_trades[group_key].append(trade)

    # Calculate group summaries
    group_summaries = {}
    for group_key, trades_in_group in grouped_trades.items():
        group_pnl = sum(t['pnl'] for t in trades_in_group if isinstance(t['pnl'], (int, float)))
        group_summaries[group_key] = {
            'count': len(trades_in_group),
            'total_pnl': group_pnl,
            'trades': trades_in_group
        }

    # Get unique values for filters
    all_instruments = list(set([t.get('instrument', 'Unknown') for t in trades]))
    all_tags = list(set([t.get('entry_tag', 'General Trades') for t in trades]))

    context = {
        'group_summaries': group_summaries,
        'closed_trades': closed_trades,
        'total_pnl': total_pnl,
        'has_active_trades': len(grouped_trades) > 0,
        'group_by': group_by,
        'group_type_display': 'Automation Batch' if group_by == 'automation_batch' else ('Day' if group_by == 'day' else 'Expiry Date'),
        'instrument_filter': instrument_filter,
        'tag_filter': tag_filter,
        'all_instruments': all_instruments,
        'all_tags': all_tags,
    }

    return render(request, 'analyzer/trades.html', context)


def settings_view(request):
    choices = ['15 Mins', '30 Mins', '1 Hour', 'Disable']
    weekdays = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]

    if request.method == 'POST':
        # Handle P&L refresh action
        if 'refresh_pnl' in request.POST:
            try:
                success = pnl_updater.force_update()
                if success:
                    messages.success(request, '✅ Active trades P&L updated successfully!')
                else:
                    messages.error(request, '❌ Failed to update P&L. Please check your connection.')
            except Exception as e:
                messages.error(request, f'❌ P&L update error: {str(e)}')
            return redirect('settings')
            
        # Handle P&L updater start/stop
        if 'toggle_pnl_updater' in request.POST:
            try:
                if pnl_updater.get_status()['is_running']:
                    pnl_updater.stop_updater()
                    messages.info(request, '🛑 Automatic P&L updates stopped')
                else:
                    pnl_updater.start_updater()
                    messages.success(request, '✅ Automatic P&L updates started (30-minute intervals)')
            except Exception as e:
                messages.error(request, f'❌ P&L updater error: {str(e)}')
            return redirect('settings')
            
        # Handle option chain refresh settings
        if 'set_option_chain_refresh' in request.POST:
            try:
                interval_minutes = int(request.POST.get('option_chain_interval', 0))
                pnl_updater.set_option_chain_refresh_interval(interval_minutes)
                
                if interval_minutes == 0:
                    messages.info(request, '🛑 Option chain refresh disabled')
                else:
                    messages.success(request, f'✅ Option chain refresh set to {interval_minutes} minute{"s" if interval_minutes != 1 else ""}')
            except Exception as e:
                messages.error(request, f'❌ Option chain refresh error: {str(e)}')
            return redirect('settings')
        
        # Get form values
        interval = request.POST.get('interval', '15 Mins')
        bot_token = request.POST.get('bot_token', '')
        chat_id = request.POST.get('chat_id', '')
        
        # Get new data refresh and auto-generation settings
        pnl_refresh_interval = request.POST.get('pnl_refresh_interval', '10sec')
        telegram_alert_interval = request.POST.get('telegram_alert_interval', '15min')
        enable_eod_summary = 'enable_eod_summary' in request.POST
        option_chain_refresh_interval = request.POST.get('option_chain_refresh_interval', '1min')
        
        # Get alert preferences
        enable_target_alerts = 'enable_target_alerts' in request.POST
        enable_stoploss_alerts = 'enable_stoploss_alerts' in request.POST
        enable_trade_alerts = 'enable_trade_alerts' in request.POST
        enable_bulk_alerts = 'enable_bulk_alerts' in request.POST
        enable_summary_alerts = 'enable_summary_alerts' in request.POST
        
        # Load current settings and update
        current_settings = utils.load_settings()
        current_settings.update({
            'update_interval': interval,
            'bot_token': bot_token,
            'chat_id': chat_id,
            
            # Data refresh settings
            'pnl_refresh_interval': pnl_refresh_interval,
            'telegram_alert_interval': telegram_alert_interval,
            'enable_eod_summary': enable_eod_summary,
            'option_chain_refresh_interval': option_chain_refresh_interval,
            
            # Alert preferences
            'enable_target_alerts': enable_target_alerts,
            'enable_stoploss_alerts': enable_stoploss_alerts,
            'enable_trade_alerts': enable_trade_alerts,
            'enable_bulk_alerts': enable_bulk_alerts,
            'enable_summary_alerts': enable_summary_alerts,
        })
        
        try:
            utils.save_settings(current_settings)
            messages.success(request, 'Settings updated successfully! All preferences have been saved.')
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')
        
        return redirect('settings')

    # Load current settings for display
    current_settings = utils.load_settings()
    
    # Get P&L updater status
    pnl_status = pnl_updater.get_status()
    
    context = {
        'settings': current_settings,
        'choices': choices,
        'weekdays': weekdays,
        'pnl_status': pnl_status
    }
    return render(request, 'analyzer/settings.html', context)


def broker_settings_view(request):
    """Dedicated broker settings view with enhanced multi-broker support"""
    
    if request.method == 'POST':
        # Handle broker account configuration
        broker_accounts = []
        if 'broker_accounts_json' in request.POST:
            try:
                broker_accounts = json.loads(request.POST.get('broker_accounts_json', '[]'))
                
                # Validate broker accounts
                for account in broker_accounts:
                    # For FlatTrade, use client_id; for others, use account_id
                    account_identifier = account.get('client_id') if account.get('broker') == 'FLATTRADE' else account.get('account_id')
                    if not account.get('broker') or not account_identifier:
                        messages.error(request, 'Invalid broker account configuration. Please check all required fields.')
                        return redirect('broker_settings')
                
                # Load current settings and update only broker settings
                current_settings = utils.load_settings()
                current_settings['broker_accounts'] = broker_accounts
                
                # Handle live trading toggle
                enable_live_trading = 'enable_live_trading' in request.POST
                auto_place_orders = 'auto_place_orders' in request.POST
                default_order_type = request.POST.get('default_order_type', 'MARKET')
                enable_position_monitoring = 'enable_position_monitoring' in request.POST
                
                # Handle lot size and auto-close settings
                nifty_lot_size = int(request.POST.get('nifty_lot_size', 25))
                banknifty_lot_size = int(request.POST.get('banknifty_lot_size', 15))
                auto_close_targets = 'auto_close_targets' in request.POST
                auto_close_stoploss = 'auto_close_stoploss' in request.POST
                
                current_settings.update({
                    'enable_live_trading': enable_live_trading,
                    'auto_place_orders': auto_place_orders,
                    'default_order_type': default_order_type,
                    'enable_position_monitoring': enable_position_monitoring,
                    'nifty_lot_size': nifty_lot_size,
                    'banknifty_lot_size': banknifty_lot_size,
                    'auto_close_targets': auto_close_targets,
                    'auto_close_stoploss': auto_close_stoploss,
                })
                
                utils.save_settings(current_settings)
                messages.success(request, f'✅ Broker settings updated successfully! {len(broker_accounts)} account(s) configured.')
                
            except json.JSONDecodeError:
                messages.error(request, 'Invalid broker accounts configuration format')
            except Exception as e:
                messages.error(request, f'Error saving broker settings: {str(e)}')
                
        return redirect('broker_settings')

    # Load current settings for display
    current_settings = utils.load_settings()
    
    # Get broker account status
    broker_accounts = current_settings.get('broker_accounts', [])
    
    # Migrate FlatTrade accounts from access_token to secret_key
    migrated = False
    for account in broker_accounts:
        if account.get('broker') == 'FLATTRADE':
            if 'access_token' in account and 'secret_key' not in account:
                account['secret_key'] = account.pop('access_token')
                migrated = True
                print(f"Migrated FlatTrade account {account.get('client_id', account.get('account_id', 'Unknown'))} from access_token to secret_key")
    
    if migrated:
        current_settings['broker_accounts'] = broker_accounts
        utils.save_settings(current_settings)
    
    # Add default FlatTrade account if none exists
    has_flattrade = any(account.get('broker') == 'FLATTRADE' for account in broker_accounts)
    if not has_flattrade:
        default_flattrade = {
            'broker': 'FLATTRADE',
            'client_id': 'FT033862',  # Single client ID
            'account_name': 'FlatTrade Account',
            'api_key': '',  # Leave empty for user to fill
            'secret_key': '',  # Leave empty for user to fill
            'enabled': True
        }
        broker_accounts.append(default_flattrade)
        current_settings['broker_accounts'] = broker_accounts
        utils.save_settings(current_settings)
    
    # Available brokers with their required fields
    available_brokers = {
        'DHAN': {
            'name': 'DhanHQ',
            'fields': ['client_id', 'access_token'],
            'description': 'Fast execution with competitive pricing',
            'logo': 'bi-bank',
            'color': '#007bff'
        },
        'ZERODHA': {
            'name': 'Zerodha Kite',
            'fields': ['api_key', 'access_token'],
            'description': 'India\'s largest discount broker',
            'logo': 'bi-graph-up',
            'color': '#ff6600'
        },
        'ANGEL': {
            'name': 'Angel Broking',
            'fields': ['api_key', 'access_token', 'client_id'],
            'description': 'Technology-driven trading platform',
            'logo': 'bi-wings',
            'color': '#e74c3c'
        },
        'UPSTOX': {
            'name': 'Upstox',
            'fields': ['api_key', 'access_token'],
            'description': 'Advanced trading technology',
            'logo': 'bi-arrow-up-circle',
            'color': '#8e44ad'
        },
        'FLATTRADE': {
            'name': 'FlatTrade',
            'fields': ['api_key', 'secret_key', 'client_id'],
            'description': 'Zero brokerage trading platform',
            'logo': 'bi-graph-down',
            'color': '#27ae60'
        }
    }
    
    context = {
        'settings': current_settings,
        'broker_accounts': broker_accounts,
        'available_brokers': available_brokers,
        'live_trading_enabled': current_settings.get('enable_live_trading', False),
        'auto_place_orders': current_settings.get('auto_place_orders', False),
        'default_order_type': current_settings.get('default_order_type', 'MARKET'),
        'enable_position_monitoring': current_settings.get('enable_position_monitoring', True),
        'nifty_lot_size': current_settings.get('nifty_lot_size', 25),
        'banknifty_lot_size': current_settings.get('banknifty_lot_size', 15),
        'auto_close_targets': current_settings.get('auto_close_targets', False),
        'auto_close_stoploss': current_settings.get('auto_close_stoploss', False),
    }
    
    return render(request, 'analyzer/broker_settings.html', context)


@require_http_methods(["POST"])
def test_telegram(request):
    """Test Telegram configuration by sending a test message."""
    try:
        data = json.loads(request.body)
        bot_token = data.get('bot_token', '').strip()
        chat_id = data.get('chat_id', '').strip()
        
        if not bot_token or not chat_id:
            return JsonResponse({
                'success': False,
                'error': 'Both bot token and chat ID are required'
            })
        
        # Send test message using the provided credentials
        test_message = f"🧪 **FiFTO Test Message**\n\n✅ Telegram integration is working correctly!\n\n📅 Test sent at: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}\n\n🤖 Your bot is ready to send trading notifications."
        
        # Use utils function to send the message with provided credentials
        success = utils.send_telegram_message_with_credentials(test_message, bot_token, chat_id)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Test message sent successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to send message. Please check your bot token and chat ID.'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        })


@require_http_methods(["POST"])
def test_broker_connection(request):
    """Test broker API connection."""
    try:
        data = json.loads(request.body)
        broker_type = data.get('broker', '').strip()
        account_config = data.get('config', {})
        
        if not broker_type or not account_config:
            return JsonResponse({
                'success': False,
                'error': 'Broker type and configuration are required'
            })
        
        # Import broker handler classes
        from .broker_manager import DhanBrokerHandler, FlatTradeBrokerHandler
        
        try:
            if broker_type == 'FLATTRADE':
                handler = FlatTradeBrokerHandler(account_config)
                result = handler.test_connection()
            elif broker_type == 'DHAN':
                handler = DhanBrokerHandler(account_config)
                # Add test connection method for other brokers if needed
                result = {'success': False, 'error': 'Test connection not implemented for DHAN yet'}
            else:
                result = {'success': False, 'error': f'Broker {broker_type} not supported for testing yet'}
            
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Broker test error: {str(e)}'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        })


# Simple test endpoint for FlatTrade
@require_http_methods(["GET"])
def test_flattrade_quick(request):
    """Quick test for FlatTrade authentication"""
    try:
        from .flattrade_api import FlatTradeBrokerHandler
        
        # Test with updated credentials
        test_config = {
            'account_id': 'FiftoNif',
            'api_key': '130f996a94c444359fac442b48deb6e9',
            'secret_key': '2025.c2818f24dab04e37b756327af571b2b90b3fc75e59621221',
            'client_id': 'FiftoNif'
        }
        
        handler = FlatTradeBrokerHandler(test_config)
        result = handler.test_connection()
        
        return JsonResponse({
            'test_result': result,
            'config_used': {
                'account_id': test_config['account_id'],
                'client_id': test_config['client_id'],
                'api_key': test_config['api_key'][:10] + '...',  # Partial key for security
                'secret_key': '***' # Hide secret key
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Test error: {str(e)}'
        })


@require_http_methods(["GET"])
def flattrade_oauth(request):
    """Initiate FlatTrade OAuth authentication"""
    try:
        client_id = request.GET.get('client_id', request.GET.get('account_id', 'default'))
        print(f"FlatTrade OAuth: Received client_id={client_id}")
        
        # Load settings to get API key
        settings = load_settings()
        broker_accounts = settings.get('broker_accounts', [])
        
        # Find the account by client_id
        account = None
        for acc in broker_accounts:
            if acc.get('broker') == 'FLATTRADE' and acc.get('client_id') == client_id:
                account = acc
                break
        
        if not account:
            print(f"Client {client_id} not found in broker_accounts")
            available_clients = [acc.get('client_id') for acc in broker_accounts if acc.get('broker') == 'FLATTRADE']
            return JsonResponse({
                'success': False,
                'error': f'Client {client_id} not found. Available FlatTrade clients: {available_clients}'
            })
        
        api_key = account.get('api_key', '')
        print(f"Found account: {account}")
        print(f"API key: {api_key[:10] if api_key else 'None'}...")
        
        if not api_key:
            return JsonResponse({
                'success': False,
                'error': 'API key not configured. Please set API Key in broker settings first.'
            })
        
        from .flattrade_api import FlatTradeBrokerHandler
        from django.conf import settings as django_settings
        
        # Using new FlatTrade API application with correct redirect URI
        # Pass client_id in state parameter since FlatTrade doesn't preserve query params
        # Make redirect URI dynamic based on current request
        current_host = request.get_host()
        redirect_uri = f"http://{current_host}/flattrade_callback/"
        
        print(f"🔗 Using redirect_uri: {redirect_uri}")
        print(f"💡 Using new FlatTrade API credentials")
        print(f"🆔 New API Key: {api_key[:10]}...")
        print(f"📝 Passing client_id in state: {client_id}")
        
        oauth_url = FlatTradeBrokerHandler.generate_oauth_url(api_key, redirect_uri, client_id)
        
        print(f"FlatTrade OAuth: api_key={api_key[:10]}..., redirect_uri={redirect_uri}")
        print(f"Generated OAuth URL: {oauth_url}")
        
        return redirect(oauth_url)
        
    except Exception as e:
        print(f"FlatTrade OAuth error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'OAuth initiation error: {str(e)}'
        })


@require_http_methods(["GET"])
def flattrade_callback(request):
    """Handle FlatTrade OAuth callback"""
    try:
        auth_code = request.GET.get('code')
        state = request.GET.get('state')
        client_param = request.GET.get('client')  # FlatTrade returns state as 'client'
        client_id = request.GET.get('client_id') or state or client_param  # Try all possible sources
        
        print(f"FlatTrade Callback: auth_code={auth_code}, state={state}, client_param={client_param}, client_id={client_id}")
        print(f"FlatTrade Callback: All GET parameters: {dict(request.GET)}")
        
        if not auth_code:
            error = request.GET.get('error', 'Unknown error')
            print(f"❌ FlatTrade Callback: No auth_code found, error={error}")
            return render(request, 'analyzer/oauth_error.html', {
                'error': error,
                'broker': 'FlatTrade'
            })
        
        if not client_id:
            print(f"❌ FlatTrade Callback: No client_id found in any parameter")
            return render(request, 'analyzer/oauth_error.html', {
                'error': 'Missing client_id in OAuth callback. Please try the OAuth flow again.',
                'broker': 'FlatTrade'
            })
        
        # Load settings to get API details
        settings = load_settings()
        broker_accounts = settings.get('broker_accounts', [])
        
        # Find the account by client_id
        account = None
        account_index = None
        for i, acc in enumerate(broker_accounts):
            if acc.get('broker') == 'FLATTRADE' and acc.get('client_id') == client_id:
                account = acc
                account_index = i
                break
        
        if not account:
            return render(request, 'analyzer/oauth_error.html', {
                'error': f'FlatTrade account with client_id {client_id} not found',
                'broker': 'FlatTrade'
            })
        
        api_key = account.get('api_key', '')
        secret_key = account.get('secret_key', '')
        
        if not all([api_key, secret_key]):
            return render(request, 'analyzer/oauth_error.html', {
                'error': 'API credentials not properly configured. Please set API Key and Secret Key in broker settings.',
                'broker': 'FlatTrade'
            })
        
        from .flattrade_api import FlatTradeBrokerHandler
        
        # Exchange auth code for access token
        success, result = FlatTradeBrokerHandler.exchange_auth_code(
            auth_code, api_key, secret_key
        )
        
        print(f"Token exchange result: success={success}, result={result}")
        
        if success:
            # Update account with new access token
            account['access_token'] = result.get('access_token')
            
            # Convert datetime to string for JSON serialization
            expires_at = result.get('expires_at')
            if expires_at:
                account['token_expiry'] = expires_at.isoformat()
            
            # Update the account in the list
            broker_accounts[account_index] = account
            settings['broker_accounts'] = broker_accounts
            
            # Save updated settings
            save_settings(settings)
            
            return render(request, 'analyzer/oauth_success.html', {
                'broker': 'FlatTrade',
                'client_id': client_id,
                'message': 'Authentication successful! Access token has been saved. You can now use FlatTrade for trading.'
            })
        else:
            error_message = result.get('error', 'Token exchange failed')
            print(f"❌ Token exchange failed for client_id {client_id}: {error_message}")
            return render(request, 'analyzer/oauth_error.html', {
                'error': f'Authentication failed for account {client_id}: {error_message}',
                'broker': 'FlatTrade'
            })
            
    except Exception as e:
        print(f"FlatTrade callback error: {e}")
        import traceback
        traceback.print_exc()
        return render(request, 'analyzer/oauth_error.html', {
            'error': f'Callback processing error: {str(e)}',
            'broker': 'FlatTrade'
        })


def flattrade_oauth_demo(request):
    """Demo page for FlatTrade OAuth"""
    settings = load_settings()
    broker_accounts = settings.get('broker_accounts', [])
    
    # Find FlatTrade account
    flattrade_account = None
    for acc in broker_accounts:
        if acc.get('broker') == 'FLATTRADE':
            flattrade_account = acc
            break
    
    context = {
        'client_id': flattrade_account.get('client_id', 'Not configured') if flattrade_account else 'Not configured',
        'api_key_display': f"{flattrade_account.get('api_key', '')[:10]}..." if flattrade_account and flattrade_account.get('api_key') else 'Not configured'
    }
    
    return render(request, 'analyzer/flattrade_oauth_demo.html', context)


def automation_view(request):
    """Handle multiple automation schedules with enhanced functionality."""
    weekdays = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Load current settings
        settings = utils.load_settings()
        multiple_schedules = settings.get('multiple_schedules', [])
        
        try:
            if action == 'create':
                # Create new schedule
                schedule_id = str(len(multiple_schedules) + int(datetime.now().timestamp()))  # Unique ID
                new_schedule = {
                    'id': schedule_id,
                    'name': request.POST.get('name', f'Schedule {len(multiple_schedules) + 1}'),
                    'enabled': 'enabled' in request.POST,
                    'time': request.POST.get('time', '09:20'),
                    'instruments': request.POST.getlist('instruments'),
                    'nifty_calc_type': request.POST.get('nifty_calc_type', 'Weekly'),
                    'banknifty_calc_type': request.POST.get('banknifty_calc_type', 'Monthly'),
                    'active_days': request.POST.getlist('active_days'),
                    'telegram_alerts': 'telegram_alerts' in request.POST,
                    'created_at': datetime.now().isoformat(),
                    'last_run': None,
                    'last_result': None,
                    
                    # Strategy Parameters
                    'target_stoploss_percent': float(request.POST.get('target_stoploss_percent', 85)),
                    'hedge_buying_percent': float(request.POST.get('hedge_buying_percent', 10)),
                    'add_to_portfolio': True,  # Always add to portfolio automatically based on strategy
                    
                    # Live trading configuration
                    'enable_live_trading': 'enable_live_trading' in request.POST,
                    'auto_place_orders': 'auto_place_orders' in request.POST,
                    'selected_broker_accounts': request.POST.getlist('selected_broker_accounts'),
                    'strategy_risk_levels': request.POST.getlist('strategy_risk_levels'),
                    
                    # Live P&L Monitoring configuration
                    'enable_trade_close': 'enable_trade_close' in request.POST,
                    'target_amount': float(request.POST.get('target_amount', 0)) if request.POST.get('target_amount') else None,
                    'stoploss_amount': float(request.POST.get('stoploss_amount', 0)) if request.POST.get('stoploss_amount') else None,
                    'alert_on_target': 'alert_on_target' in request.POST,
                    'alert_on_stoploss': 'alert_on_stoploss' in request.POST,
                }
                multiple_schedules.append(new_schedule)
                
                settings['multiple_schedules'] = multiple_schedules
                utils.save_settings(settings)
                
                # Start the permanent schedule
                if new_schedule['enabled']:
                    utils.start_permanent_schedule(new_schedule)
                
                # Add to recent activities
                utils.add_automation_activity('Schedule Created', f"Created new schedule: {new_schedule['name']}", 'success')
                
                return JsonResponse({'success': True, 'message': 'Schedule created and started successfully!'})
                
            elif action == 'update':
                # Update existing schedule
                schedule_id = request.POST.get('schedule_id')
                schedule_index = next((i for i, s in enumerate(multiple_schedules) if s['id'] == schedule_id), None)
                
                if schedule_index is not None:
                    old_schedule = multiple_schedules[schedule_index].copy()
                    multiple_schedules[schedule_index].update({
                        'name': request.POST.get('name', f'Schedule {schedule_index + 1}'),
                        'enabled': 'enabled' in request.POST,
                        'time': request.POST.get('time', '09:20'),
                        'instruments': request.POST.getlist('instruments'),
                        'nifty_calc_type': request.POST.get('nifty_calc_type', 'Weekly'),
                        'banknifty_calc_type': request.POST.get('banknifty_calc_type', 'Monthly'),
                        'active_days': request.POST.getlist('active_days'),
                        'telegram_alerts': 'telegram_alerts' in request.POST,
                        
                        # Strategy Parameters
                        'target_stoploss_percent': float(request.POST.get('target_stoploss_percent', 85)),
                        'hedge_buying_percent': float(request.POST.get('hedge_buying_percent', 10)),
                        'add_to_portfolio': True,  # Always add to portfolio automatically based on strategy
                        
                        # Live trading configuration
                        'enable_live_trading': 'enable_live_trading' in request.POST,
                        'auto_place_orders': 'auto_place_orders' in request.POST,
                        'selected_broker_accounts': request.POST.getlist('selected_broker_accounts'),
                        'strategy_risk_levels': request.POST.getlist('strategy_risk_levels'),
                        
                        # Live P&L Monitoring configuration
                        'enable_trade_close': 'enable_trade_close' in request.POST,
                        'target_amount': float(request.POST.get('target_amount', 0)) if request.POST.get('target_amount') else None,
                        'stoploss_amount': float(request.POST.get('stoploss_amount', 0)) if request.POST.get('stoploss_amount') else None,
                        'alert_on_target': 'alert_on_target' in request.POST,
                        'alert_on_stoploss': 'alert_on_stoploss' in request.POST,
                    })
                    
                    settings['multiple_schedules'] = multiple_schedules
                    utils.save_settings(settings)
                    
                    # Restart schedule if enabled
                    utils.stop_permanent_schedule(schedule_id)
                    if multiple_schedules[schedule_index]['enabled']:
                        utils.start_permanent_schedule(multiple_schedules[schedule_index])
                    
                    # Add to recent activities
                    utils.add_automation_activity('Schedule Updated', f"Updated schedule: {multiple_schedules[schedule_index]['name']}", 'success')
                    
                    return JsonResponse({'success': True, 'message': 'Schedule updated successfully!'})
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid schedule ID'})
                    
            elif action == 'get_schedule':
                # Get schedule data for editing
                schedule_id = request.POST.get('schedule_id')
                schedule = next((s for s in multiple_schedules if s['id'] == schedule_id), None)
                
                if schedule:
                    return JsonResponse({'success': True, 'schedule': schedule})
                else:
                    return JsonResponse({'success': False, 'message': 'Schedule not found'})
                    
            elif action == 'toggle':
                # Toggle schedule enabled/disabled
                schedule_id = request.POST.get('schedule_id')
                enabled = request.POST.get('enabled') == 'true'
                
                schedule_index = next((i for i, s in enumerate(multiple_schedules) if s['id'] == schedule_id), None)
                if schedule_index is not None:
                    multiple_schedules[schedule_index]['enabled'] = enabled
                    settings['multiple_schedules'] = multiple_schedules
                    utils.save_settings(settings)
                    
                    if enabled:
                        utils.start_permanent_schedule(multiple_schedules[schedule_index])
                    else:
                        utils.stop_permanent_schedule(schedule_id)
                    
                    # Add to recent activities
                    action_text = "enabled" if enabled else "disabled"
                    utils.add_automation_activity(f'Schedule {action_text.title()}', f"Schedule '{multiple_schedules[schedule_index]['name']}' {action_text}", 'success')
                    
                    return JsonResponse({'success': True, 'message': f'Schedule {"enabled" if enabled else "disabled"} successfully!'})
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid schedule ID'})
                    
            elif action == 'delete':
                # Delete schedule
                schedule_id = request.POST.get('schedule_id')
                schedule_index = next((i for i, s in enumerate(multiple_schedules) if s['id'] == schedule_id), None)
                
                if schedule_index is not None:
                    schedule_name = multiple_schedules[schedule_index]['name']
                    utils.stop_permanent_schedule(schedule_id)
                    del multiple_schedules[schedule_index]
                    
                    settings['multiple_schedules'] = multiple_schedules
                    utils.save_settings(settings)
                    
                    # Add to recent activities
                    utils.add_automation_activity('Schedule Deleted', f"Deleted schedule: {schedule_name}", 'warning')
                    
                    return JsonResponse({'success': True, 'message': 'Schedule deleted successfully!'})
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid schedule ID'})
                    
            elif action == 'test':
                # Test specific schedule
                schedule_id = request.POST.get('schedule_id')
                schedule = next((s for s in multiple_schedules if s['id'] == schedule_id), None)
                
                if schedule:
                    if not schedule['enabled']:
                        return JsonResponse({'success': False, 'message': 'This schedule is disabled'})
                    
                    if not schedule['instruments']:
                        return JsonResponse({'success': False, 'message': 'No instruments selected for this schedule'})
                    
                    # Test the schedule
                    result = utils.test_specific_automation(schedule)
                    
                    # Add to recent activities
                    utils.add_automation_activity('Manual Test', f"Tested schedule: {schedule['name']}", 'success')
                    
                    # Check if charts were generated successfully
                    charts_generated = "✅" in result
                    
                    return JsonResponse({
                        'success': True, 
                        'message': f"Test completed for '{schedule['name']}':\n\n{result}",
                        'charts_generated': charts_generated
                    })
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid schedule ID'})
                    
            elif action == 'get_recent_activities':
                # Get recent automation activities
                activities = utils.get_recent_automation_activities(limit=10)
                return JsonResponse({'success': True, 'activities': activities})
                
            elif action == 'create_test_activity':
                # Create a test activity for debugging
                utils.add_automation_activity(
                    'Test Activity', 
                    f'Test activity created at {datetime.now().strftime("%I:%M:%S %p")}', 
                    'success'
                )
                return JsonResponse({'success': True, 'message': 'Test activity created successfully!'})
                
            elif action == 'toggle_auto_portfolio':
                # Toggle auto portfolio feature
                enabled = request.POST.get('enabled') == 'true'
                settings['auto_portfolio_enabled'] = enabled
                utils.save_settings(settings)
                
                return JsonResponse({'success': True, 'message': f'Auto-portfolio {"enabled" if enabled else "disabled"} successfully!'})
                    
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
    
    # Load current settings for display
    current_settings = utils.load_settings()
    multiple_schedules = current_settings.get('multiple_schedules', [])
    
    # Add last run information to schedules
    for schedule in multiple_schedules:
        if 'last_run' not in schedule:
            schedule['last_run'] = None
        if 'last_result' not in schedule:
            schedule['last_result'] = None
    
    # Get broker accounts for schedule configuration
    broker_accounts = current_settings.get('broker_accounts', [])
    enabled_broker_accounts = []
    for account in broker_accounts:
        if account.get('enabled', False):
            # For FlatTrade, use client_id; for others, use account_id
            account_id = account.get('client_id') if account.get('broker') == 'FLATTRADE' else account.get('account_id')
            if account_id:
                enabled_broker_accounts.append({
                    'id': account_id,
                    'name': account.get('account_name', account_id),
                    'broker': account.get('broker'),
                })
    
    context = {
        'multiple_schedules': multiple_schedules,
        'weekdays': weekdays,
        'settings': current_settings,
        'recent_activities': utils.get_recent_automation_activities(10),
        'broker_accounts': enabled_broker_accounts,
    }
    return render(request, 'analyzer/automation.html', context)


def closed_trades_view(request):
    """Display closed trades with filtering and statistics."""
    
    # Handle POST requests for delete operations
    if request.method == 'POST':
        action = request.POST.get('action')
        all_trades = utils.load_trades()
        
        if action == 'delete_closed_trade':
            trade_id = request.POST.get('trade_id')
            original_count = len(all_trades)
            all_trades = [t for t in all_trades if t['id'] != trade_id]
            deleted_count = original_count - len(all_trades)
            utils.save_trades(all_trades)
            if deleted_count > 0:
                utils.send_telegram_message(f"🗑️ Closed Trade Deleted: {trade_id}")
                messages.success(request, f'Closed trade {trade_id} deleted successfully.')
            else:
                messages.error(request, f'Trade {trade_id} not found.')
            return redirect('closed_trades')
            
        elif action == 'delete_all_closed':
            original_count = len(all_trades)
            # Keep only running trades
            active_trades = [t for t in all_trades if t.get('status') == 'Running']
            deleted_count = original_count - len(active_trades)
            utils.save_trades(active_trades)
            if deleted_count > 0:
                utils.send_telegram_message(f"🗑️ Bulk Delete: All {deleted_count} closed trades deleted")
                messages.success(request, f'Deleted all {deleted_count} closed trades successfully.')
            else:
                messages.info(request, 'No closed trades found to delete.')
            return redirect('closed_trades')
    
    # Get all trades and filter for closed ones
    all_trades = utils.load_trades()
    closed_trades = [t for t in all_trades if t.get('status') in ['Target', 'Stoploss', 'Manually Closed', 'Auto Closed - Target Hit', 'Auto Closed - Stoploss Hit']]
    
    # Apply sorting based on user selection
    sort_option = request.GET.get('sort', 'newest')
    
    # Fix missing data for existing closed trades first
    from datetime import datetime
    for trade in closed_trades:
        # Fix missing closed_date
        if 'closed_date' not in trade or not trade['closed_date']:
            trade['closed_date'] = datetime.now()
        elif isinstance(trade['closed_date'], str):
            try:
                # Try to parse ISO format
                trade['closed_date'] = datetime.fromisoformat(trade['closed_date'].replace('Z', '+00:00'))
            except:
                trade['closed_date'] = datetime.now()
        
        # Fix missing final_pnl
        if 'final_pnl' not in trade or trade['final_pnl'] is None:
            # Use current pnl if available, otherwise calculate it
            if 'pnl' in trade and trade['pnl'] is not None:
                trade['final_pnl'] = trade['pnl']
            else:
                # Calculate P&L based on trade status
                try:
                    # If it's a target hit, estimate positive P&L
                    if 'Target' in trade.get('status', ''):
                        target_amount = trade.get('target_amount', 0)
                        if target_amount > 0:
                            trade['final_pnl'] = target_amount
                    # If it's a stoploss hit, estimate negative P&L
                    elif 'Stoploss' in trade.get('status', ''):
                        stoploss_amount = trade.get('stoploss_amount', 0)
                        if stoploss_amount > 0:
                            trade['final_pnl'] = -stoploss_amount
                    else:
                        trade['final_pnl'] = 0
                except:
                    trade['final_pnl'] = 0
    
    # Apply sorting
    if sort_option == 'newest':
        closed_trades.sort(key=lambda x: x.get('closed_date', datetime.now()), reverse=True)
    elif sort_option == 'oldest':
        closed_trades.sort(key=lambda x: x.get('closed_date', datetime.now()))
    elif sort_option == 'profit_high':
        closed_trades.sort(key=lambda x: x.get('final_pnl', 0), reverse=True)
    elif sort_option == 'profit_low':
        closed_trades.sort(key=lambda x: x.get('final_pnl', 0))
    elif sort_option == 'target_hit':
        # Filter and sort target hit trades
        closed_trades = [t for t in closed_trades if 'Target' in t.get('status', '')]
        closed_trades.sort(key=lambda x: x.get('closed_date', datetime.now()), reverse=True)
    elif sort_option == 'stoploss_hit':
        # Filter and sort stoploss hit trades
        closed_trades = [t for t in closed_trades if 'Stoploss' in t.get('status', '')]
        closed_trades.sort(key=lambda x: x.get('closed_date', datetime.now()), reverse=True)
    
    # Calculate statistics
    total_profit = sum(t.get('final_pnl', 0) for t in closed_trades if t.get('final_pnl', 0) > 0)
    total_loss = abs(sum(t.get('final_pnl', 0) for t in closed_trades if t.get('final_pnl', 0) < 0))
    net_pnl = total_profit - total_loss
    
    profitable_trades = len([t for t in closed_trades if t.get('final_pnl', 0) > 0])
    total_closed = len(closed_trades)
    win_rate = (profitable_trades / total_closed * 100) if total_closed > 0 else 0
    
    # Get available tags for reference (optional)
    available_tags = list(set(t.get('entry_tag', 'General') for t in all_trades if t.get('entry_tag')))
    available_tags = sorted([tag for tag in available_tags if tag])

    context = {
        'closed_trades': closed_trades,
        'total_profit': total_profit,
        'total_loss': total_loss,
        'net_pnl': net_pnl,
        'win_rate': win_rate,
        'sort': sort_option,
        'available_tags': available_tags,
    }
    
    return render(request, 'analyzer/closed_trades.html', context)

def test_automation_view(request):
    """Test automation functionality manually."""
    if request.method == 'POST':
        try:
            # For testing, we'll create a special test mode
            settings = utils.load_settings()
            
            # Check if automation is enabled
            if not settings.get('enable_auto_generation', False):
                return JsonResponse({
                    'success': False, 
                    'message': 'Automation is disabled. Please enable automation first.'
                })
            
            # Check if instruments are selected
            auto_gen_instruments = settings.get('auto_gen_instruments', [])
            if not auto_gen_instruments:
                return JsonResponse({
                    'success': False, 
                    'message': 'No instruments selected. Please select NIFTY and/or BANKNIFTY.'
                })
            
            # For testing - bypass market hours and day checks
            from datetime import datetime
            from django.utils import timezone
            import pytz
            
            ist_tz = pytz.timezone('Asia/Kolkata')
            current_time = timezone.now().astimezone(ist_tz)
            
            results = []
            nifty_calc_type = settings.get('nifty_calc_type', 'Weekly')
            banknifty_calc_type = settings.get('banknifty_calc_type', 'Monthly')
            
            # Generate expiry date (next Thursday for weekly, next month end for monthly)
            def get_next_expiry(calc_type):
                from datetime import timedelta
                today = current_time
                if calc_type == 'Weekly':
                    # Find next Thursday
                    days_ahead = 3 - today.weekday()  # Thursday is 3
                    if days_ahead <= 0:  # Thursday already passed
                        days_ahead += 7
                    next_expiry = today + timedelta(days=days_ahead)
                else:  # Monthly
                    # Find last Thursday of current month or next month
                    next_month = today.replace(day=28) + timedelta(days=4)
                    last_day = next_month - timedelta(days=next_month.day)
                    # Find last Thursday
                    last_thursday = last_day - timedelta(days=(last_day.weekday() - 3) % 7)
                    if last_thursday <= today:
                        # Next month
                        next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
                        next_month_last = (next_month.replace(day=28) + timedelta(days=4)) - timedelta(days=(next_month.replace(day=28) + timedelta(days=4)).day)
                        next_expiry = next_month_last - timedelta(days=(next_month_last.weekday() - 3) % 7)
                    else:
                        next_expiry = last_thursday
                
                return next_expiry.strftime('%d-%b-%Y')
            
            for instrument in auto_gen_instruments:
                try:
                    calc_type = nifty_calc_type if instrument == 'NIFTY' else banknifty_calc_type
                    expiry = get_next_expiry(calc_type)
                    
                    # Generate analysis with auto-add to portfolio
                    analysis_data, status_message = utils.generate_and_auto_add_analysis(
                        instrument, calc_type, expiry, auto_add=True
                    )
                    
                    if analysis_data:
                        result = f"✅ {instrument} {calc_type}: {status_message}"
                        results.append(result)
                    else:
                        error_result = f"❌ {instrument} {calc_type}: {status_message}"
                        results.append(error_result)
                        
                except Exception as e:
                    error_result = f"❌ {instrument}: Error - {str(e)}"
                    results.append(error_result)
            
            final_result = f"🧪 TEST MODE - Manual Automation Run\n\n" + "\n".join(results)
            
            return JsonResponse({
                'success': True, 
                'message': final_result
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'Automation test failed: {str(e)}'
            })
    else:
        return JsonResponse({'success': False, 'message': 'Only POST method allowed'})


def close_trade(request, trade_id):
    utils.close_selected_trade(trade_id)
    messages.success(request, f"Square-off alert for {trade_id} sent.")
    return redirect(reverse('trades_list'))

def send_charts(request):
    analysis_data = request.session.get('analysis_data')
    if not analysis_data:
        messages.warning(request, 'No analysis data found to send.')
        return redirect(reverse('index'))
    status = utils.send_daily_chart_to_telegram(analysis_data)
    messages.info(request, f"Telegram status: {status}")
    return redirect(reverse('index'))

def automation_multiple_view(request):
    """Handle multiple automation configurations."""
    weekdays = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    ]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Load current multiple automations
        settings = utils.load_settings()
        multiple_automations = settings.get('multiple_automations', [])
        
        try:
            if action == 'create':
                # Create new automation
                new_automation = {
                    'id': len(multiple_automations),
                    'name': request.POST.get('name', f'Schedule {len(multiple_automations) + 1}'),
                    'enabled': 'enabled' in request.POST,
                    'days': request.POST.getlist('days'),
                    'time': request.POST.get('time', '09:20'),
                    'instruments': request.POST.getlist('instruments'),
                    'nifty_calc_type': request.POST.get('nifty_calc_type', 'Weekly'),
                    'banknifty_calc_type': request.POST.get('banknifty_calc_type', 'Monthly'),
                }
                multiple_automations.append(new_automation)
                
                settings['multiple_automations'] = multiple_automations
                utils.save_settings(settings)
                
                return JsonResponse({'success': True, 'message': 'Automation created successfully!'})
                
            elif action == 'update':
                # Update existing automation
                automation_id = int(request.POST.get('automation_id'))
                if 0 <= automation_id < len(multiple_automations):
                    multiple_automations[automation_id].update({
                        'name': request.POST.get('name', f'Schedule {automation_id + 1}'),
                        'enabled': 'enabled' in request.POST,
                        'days': request.POST.getlist('days'),
                        'time': request.POST.get('time', '09:20'),
                        'instruments': request.POST.getlist('instruments'),
                        'nifty_calc_type': request.POST.get('nifty_calc_type', 'Weekly'),
                        'banknifty_calc_type': request.POST.get('banknifty_calc_type', 'Monthly'),
                    })
                    
                    settings['multiple_automations'] = multiple_automations
                    utils.save_settings(settings)
                    
                    return JsonResponse({'success': True, 'message': 'Automation updated successfully!'})
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid automation ID'})
                    
            elif action == 'delete':
                # Delete automation
                automation_id = int(request.POST.get('automation_id'))
                if 0 <= automation_id < len(multiple_automations):
                    del multiple_automations[automation_id]
                    
                    # Reindex remaining automations
                    for i, automation in enumerate(multiple_automations):
                        automation['id'] = i
                    
                    settings['multiple_automations'] = multiple_automations
                    utils.save_settings(settings)
                    
                    return JsonResponse({'success': True, 'message': 'Automation deleted successfully!'})
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid automation ID'})
                    
            elif action == 'test':
                # Test specific automation
                automation_id = int(request.POST.get('automation_id'))
                if 0 <= automation_id < len(multiple_automations):
                    automation = multiple_automations[automation_id]
                    
                    if not automation['enabled']:
                        return JsonResponse({'success': False, 'message': 'This automation schedule is disabled'})
                    
                    if not automation['instruments']:
                        return JsonResponse({'success': False, 'message': 'No instruments selected for this schedule'})
                    
                    # Test the automation
                    result = utils.test_specific_automation(automation)
                    return JsonResponse({'success': True, 'message': f"Test completed for '{automation['name']}':\n\n{result}"})
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid automation ID'})
                    
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
    
    # Load current settings for display
    current_settings = utils.load_settings()
    multiple_automations = current_settings.get('multiple_automations', [])
    
    context = {
        'automations': multiple_automations,
        'weekdays': weekdays
    }
    return render(request, 'analyzer/automation_multiple.html', context)


def option_chain_view(request):
    """
    Option Chain view for NIFTY and BANKNIFTY with basket order functionality
    """
    instrument = request.GET.get('instrument', 'NIFTY')
    expiry = request.GET.get('expiry', None)
    
    try:
        # Set current expiry if not provided
        if not expiry:
            expiry_dates = utils.get_option_chain_expiry_dates_only(instrument)
            if expiry_dates:
                expiry = expiry_dates[0]  # Use first (nearest) expiry only
        
        # Try to load from cache first for faster loading
        cached_data = utils.load_option_chain_cache(instrument, expiry, max_age_minutes=3)
        if cached_data:
            print(f"💾 Using cached option chain data for {instrument} {expiry}")
            option_chain_data = cached_data
        else:
            # Get fresh NSE option chain data
            option_chain_data = utils._fetch_fresh_option_chain_data(instrument)
            
            # Save to cache for future use
            if option_chain_data:
                utils.save_option_chain_cache(instrument, expiry, option_chain_data)
        
        # Initialize context with defaults
        context = {
            'instrument': instrument,
            'instruments': ['NIFTY', 'BANKNIFTY'],
            'option_chain': None,
            'expiry_dates': [],
            'current_expiry': expiry,
            'underlying_price': 0,
            'strikes': [],
            'symbol': instrument,
            'error_message': None,
            'option_chain_refresh_status': get_option_chain_refresh_status()
        }
        
        if option_chain_data and 'data' in option_chain_data:
            data = option_chain_data['data']
            underlying_price = data.get('last_price', 0)
            strikes_dict = data.get('oc', {})
            expiry_dates = option_chain_data.get('expiryDates', [])
            
            # Set current expiry
            if not expiry and expiry_dates:
                expiry = expiry_dates[0]
                context['current_expiry'] = expiry
            
            # Process strikes data for display
            strikes_data = []
            for strike_str, strike_data in strikes_dict.items():
                try:
                    strike = float(strike_str)
                    ce_data = strike_data.get('ce', {})
                    pe_data = strike_data.get('pe', {})
                    
                    # Create CE and PE objects to match template expectations
                    ce_obj = {
                        'ltp': ce_data.get('last_price', 0),
                        'change': ce_data.get('day_change', 0),
                        'oi': ce_data.get('oi', 0),
                        'volume': ce_data.get('volume', 0),
                        'iv': round(ce_data.get('implied_volatility', 0), 2),
                        'bid': ce_data.get('top_bid_price', 0),
                        'ask': ce_data.get('top_ask_price', 0),
                    }
                    
                    pe_obj = {
                        'ltp': pe_data.get('last_price', 0),
                        'change': pe_data.get('day_change', 0),
                        'oi': pe_data.get('oi', 0),
                        'volume': pe_data.get('volume', 0),
                        'iv': round(pe_data.get('implied_volatility', 0), 2),
                        'bid': pe_data.get('top_bid_price', 0),
                        'ask': pe_data.get('top_ask_price', 0),
                    }
                    
                    strike_obj = {
                        'strike_price': int(strike),
                        'CE': type('obj', (object,), ce_obj),
                        'PE': type('obj', (object,), pe_obj),
                        'has_max_oi': False  # Will be calculated later
                    }
                    
                    strikes_data.append(strike_obj)
                except (ValueError, TypeError):
                    continue
            
            # Sort by strike price and filter around current price
            strikes_data.sort(key=lambda x: x['strike_price'])
            
            # Filter strikes around current price (±1000 points for more data)
            if underlying_price > 0:
                min_strike = max(10000, underlying_price - 1000)
                max_strike = min(50000, underlying_price + 1000)
                strikes_data = [s for s in strikes_data if min_strike <= s['strike_price'] <= max_strike]
            
            # Calculate max OI for highlighting
            if strikes_data:
                max_ce_oi = max(s['CE'].oi for s in strikes_data)
                max_pe_oi = max(s['PE'].oi for s in strikes_data)
                
                for strike_obj in strikes_data:
                    if strike_obj['CE'].oi == max_ce_oi or strike_obj['PE'].oi == max_pe_oi:
                        strike_obj['has_max_oi'] = True
            
            context.update({
                'option_chain': option_chain_data,
                'expiry_dates': [expiry] if expiry else expiry_dates[:1],  # Only current expiry
                'underlying_price': underlying_price,
                'strikes': strikes_data[:50],  # First 50 relevant strikes for more data
                'symbol': instrument,  # Add symbol for JavaScript
            })
            
            print(f"✅ Context updated successfully with {len(strikes_data[:50])} strikes - CURRENT EXPIRY ONLY: {expiry}")
            
            # Debug logging
            print(f"🔍 Option Chain Debug - Symbol: {instrument}, Strikes Count: {len(strikes_data[:50])}")
            if strikes_data and len(strikes_data) > 0:
                first_strike = strikes_data[0]
                print(f"📊 First strike sample: Strike={first_strike['strike_price']}")
                print(f"📊 CE LTP={first_strike.get('CE', {}).get('ltp', 'N/A')}, PE LTP={first_strike.get('PE', {}).get('ltp', 'N/A')}")
                print(f"📦 Template context keys: instrument={instrument}, current_expiry={expiry}, strikes count={len(strikes_data[:50])}")
            else:
                print("⚠️  No strikes data found!")
            
            print(f"🔵 End of successful processing block")
            
        else:
            print("❌ Entering ELSE clause - option chain data failed")
            context['error_message'] = f"Could not load option chain data for {instrument}"
            
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        # Only override context if it doesn't have valid data
        if 'strikes' not in context or len(context.get('strikes', [])) == 0:
            context = {
                'instrument': instrument,
                'instruments': ['NIFTY', 'BANKNIFTY'],
                'option_chain': None,
                'expiry_dates': [],
                'current_expiry': expiry,
                'underlying_price': 0,
                'strikes': [],
                'symbol': instrument,
                'error_message': f"Error loading option chain: {str(e)}"
            }
        else:
            # Preserve successful data - don't set error_message to avoid hiding table
            print(f"⚠️ Exception occurred but preserving {len(context.get('strikes', []))} strikes")
    
    print(f"🎯 Final context before template: strikes={len(context.get('strikes', []))}, instrument={context.get('instrument', 'None')}")
    
    return render(request, 'analyzer/option_chain.html', context)


def get_option_chain_refresh_status():
    """
    Get the current option chain refresh status - Always disabled for manual terminal fetch
    """
    # Auto-refresh disabled to allow manual terminal data fetching
    return "Off"


@csrf_exempt
@require_http_methods(["POST"])
def set_option_chain_refresh(request):
    """
    Set option chain refresh interval - Disabled for manual terminal fetch
    """
    # Auto-refresh functionality disabled to allow manual terminal data fetching
    return JsonResponse({
        'success': False,
        'message': 'Auto-refresh disabled. Use terminal for manual data fetching.',
        'status': 'Off'
    })


@csrf_exempt
@require_http_methods(["POST"])
def create_basket_order(request):
    """
    Create basket order from selected option strikes
    """
    try:
        data = json.loads(request.body)
        
        selected_options = data.get('selected_options', [])
        basket_name = data.get('basket_name', f"Basket_{datetime.now().strftime('%Y%m%d_%I%M%p')}")
        
        if not selected_options:
            return JsonResponse({'success': False, 'message': 'No options selected'})
        
        # Transform option data to match template expectations
        transformed_options = []
        for option in selected_options:
            transformed_option = {
                'instrument': option.get('symbol', ''),
                'strike': option.get('strike_price', 0),
                'type': option.get('option_type', ''),
                'action': option.get('action', ''),
                'quantity': option.get('quantity', 1),
                'order_type': option.get('order_type', 'MARKET'),
                'ltp': 0  # Will be fetched from market data if needed
            }
            transformed_options.append(transformed_option)
        
        # Save basket order to session
        basket_orders = request.session.get('basket_orders', [])
        
        new_basket = {
            'id': len(basket_orders) + 1,
            'name': basket_name,
            'created_at': datetime.now().isoformat(),
            'options': transformed_options,
            'status': 'created'
        }
        
        basket_orders.append(new_basket)
        request.session['basket_orders'] = basket_orders
        
        return JsonResponse({
            'success': True, 
            'message': f'Basket order "{basket_name}" created with {len(selected_options)} options',
            'basket_id': new_basket['id']
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error creating basket: {str(e)}'})


def basket_orders_view(request):
    """
    View all basket orders
    """
    basket_orders = request.session.get('basket_orders', [])
    
    context = {
        'basket_orders': basket_orders
    }
    
    return render(request, 'analyzer/basket_orders.html', context)


@require_http_methods(["POST"])
def clear_all_baskets(request):
    """
    Clear all basket orders from session
    """
    try:
        # Clear all basket orders from session
        request.session['basket_orders'] = []
        return JsonResponse({
            'success': True, 
            'message': 'All baskets cleared successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Error clearing baskets: {str(e)}'
        })

def nse_test_view(request):
    """
    NSE Data Sources Test Dashboard
    """
    context = {
        'page_title': 'NSE Data Sources Test',
        'description': 'Test and monitor all available market data sources'
    }
    
    return render(request, 'analyzer/nse_test.html', context)