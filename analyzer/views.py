# analyzer/views.py - Clean New Implementation

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
import json
import pandas as pd
import os
from datetime import datetime
from collections import defaultdict
from . import utils
from .utils import generate_analysis, load_settings, save_settings

def index(request):
    # Handle session clearing
    if request.method == 'POST' and request.POST.get('clear_session'):
        request.session.pop('analysis_data', None)
        return JsonResponse({'status': 'cleared'})
    
    analysis_data = request.session.get('analysis_data')
    instrument = request.GET.get('instrument', 'NIFTY')
    chain = utils.get_option_chain_data(instrument)
    expiries = []
    if chain and 'records' in chain and 'expiryDates' in chain['records']:
        expiries = sorted(
            [d for d in chain['records']['expiryDates'] if datetime.strptime(d, "%d-%b-%Y").date() >= datetime.now().date()],
            key=lambda x: datetime.strptime(x, "%d-%b-%Y")
        )
    context = {
        'expiries': expiries,
        'instrument': instrument,
        'analysis_data': analysis_data
    }
    return render(request, 'analyzer/index.html', context)

def generate_and_show_analysis(request):
    # Create a debug log file
    debug_file = r"C:\Users\manir\Desktop\debug_log.txt"
    
    def debug_log(message):
        with open(debug_file, 'a', encoding='utf-8') as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
        print(message)  # Also print to console
    
    debug_log("=== Generate Analysis View Called ===")
    debug_log(f"Request method: {request.method}")
    
    if request.method == 'POST':
        instrument = request.POST.get('instrument')
        calc_type = request.POST.get('calc_type')
        expiry = request.POST.get('expiry')
        
        debug_log(f"Form data received:")
        debug_log(f"  Instrument: {instrument}")
        debug_log(f"  Calculation Type: {calc_type}")
        debug_log(f"  Expiry: {expiry}")
        
        try:
            debug_log("Calling utils.generate_analysis()...")
            analysis_data, status = utils.generate_analysis(instrument, calc_type, expiry)
            debug_log(f"Analysis result: {type(analysis_data)}, Status: {status}")
            
            if analysis_data:
                request.session['analysis_data'] = analysis_data
                messages.success(request, status)
                debug_log("✅ Analysis successful - data saved to session")
            else:
                messages.error(request, status)
                debug_log(f"❌ Analysis failed: {status}")
        except Exception as e:
            error_msg = f"Error generating analysis: {str(e)}"
            messages.error(request, error_msg)
            debug_log(f"❌ Exception occurred: {error_msg}")
            import traceback
            debug_log(f"Traceback: {traceback.format_exc()}")
        
        return redirect(reverse('index'))
    
    debug_log("❌ Non-POST request - redirecting to index")
    return redirect(reverse('index'))

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
# In analyzer/views.py

# analyzer/views.py

# In analyzer/views.py

def trades_list(request):
    trades = utils.load_trades()
    
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
            
            # Get market data for P&L calculation
            nifty_chain = utils.get_option_chain_data("NIFTY")
            banknifty_chain = utils.get_option_chain_data("BANKNIFTY")
            
            closed_count = 0
            for trade in trades:
                if trade['id'] == trade_id:
                    # Calculate actual current P&L before closing
                    chain_data = nifty_chain if trade['instrument'] == 'NIFTY' else banknifty_chain
                    current_ce, current_pe = 0.0, 0.0
                    
                    if chain_data and chain_data.get('records', {}).get('data'):
                        for item in chain_data['records']['data']:
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
                        # Fallback if market data unavailable
                        current_pnl = trade.get('pnl', 0)
                    
                    # Close the trade with actual P&L
                    trade['status'] = 'Manually Closed'
                    trade['final_pnl'] = current_pnl
                    trade['closed_date'] = datetime.now().isoformat()
                    closed_count += 1
                    break
            utils.save_trades(trades)
            # Send Telegram notification
            utils.send_telegram_message(f"📝 Manual Close: Trade {trade_id} closed with P&L ₹{current_pnl:.2f}")
            messages.success(request, f'Trade {trade_id} closed successfully with P&L ₹{current_pnl:.2f}.')
            return redirect('trades_list')
            
        elif action == 'delete_multiple':
            trade_ids = request.POST.getlist('selected_trades')
            original_count = len(trades)
            trades = [t for t in trades if t['id'] not in trade_ids]
            deleted_count = original_count - len(trades)
            utils.save_trades(trades)
            # Send Telegram notification
            utils.send_telegram_message(f"🗑️ Bulk Delete: {deleted_count} trades deleted")
            messages.success(request, f'Deleted {deleted_count} trades successfully.')
            return redirect('trades_list')
            
        elif action == 'close_multiple':
            trade_ids = request.POST.getlist('selected_trades')
            closed_count = 0
            total_pnl = 0
            for trade in trades:
                if trade['id'] in trade_ids:
                    # Calculate real P&L using current market data
                    try:
                        if trade.get('symbol') and trade.get('strike') and trade.get('option_type'):
                            symbol = trade['symbol'].replace(' ', '%20')  # URL encode spaces
                            market_data = utils.get_option_chain(symbol)
                            
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
                        start_dt = datetime.strptime(trade['start_time'], "%Y-%m-%d %H:%M")
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
                        start_dt = datetime.strptime(trade['start_time'], "%Y-%m-%d %H:%M")
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
    
    # Get market data
    nifty_chain = utils.get_option_chain_data("NIFTY")
    banknifty_chain = utils.get_option_chain_data("BANKNIFTY")

    for trade in active_trades:
        try:
            # Parse and format the date tag
            start_dt = datetime.strptime(trade['start_time'], "%Y-%m-%d %H:%M")
            display_tag = f"{start_dt.strftime('%d-%b')} {trade.get('entry_tag', '')}"
            trade['display_tag'] = display_tag
        except (ValueError, KeyError):
            trade['display_tag'] = trade.get('entry_tag', 'General Trades')

        # Calculate current P&L
        chain_data = nifty_chain if trade['instrument'] == 'NIFTY' else banknifty_chain
        current_ce, current_pe = 0.0, 0.0
        
        if chain_data and chain_data.get('records', {}).get('data'):
            for item in chain_data['records']['data']:
                if item.get("expiryDate") == trade.get('expiry'):
                    if item.get("strikePrice") == trade.get('ce_strike') and item.get("CE"):
                        current_ce = item["CE"]["lastPrice"]
                    if item.get("strikePrice") == trade.get('pe_strike') and item.get("PE"):
                        current_pe = item["PE"]["lastPrice"]
        
        lot_size = utils.get_lot_size(trade['instrument'])
        initial_premium = trade.get('initial_premium', 0)
        current_premium = current_ce + current_pe
        
        if current_premium > 0:
            pnl = round((initial_premium - current_premium) * lot_size, 2)
            trade['pnl'] = pnl
            trade['current_premium'] = current_premium
            total_pnl += pnl
            
            # Check for target/stoploss and send alerts
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
            trade['pnl'] = "N/A"
            trade['current_premium'] = "N/A"
        
        # Group by automation_batch, day, or expiry
        if group_by == 'automation_batch':
            # Group by automation generation (one automation creates one batch)
            group_key = trade.get('entry_tag', 'General Trades')
        elif group_by == 'day':
            # Group by day
            try:
                start_dt = datetime.strptime(trade['start_time'], "%Y-%m-%d %H:%M")
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
        # Get form values
        interval = request.POST.get('interval', '15 Mins')
        bot_token = request.POST.get('bot_token', '')
        chat_id = request.POST.get('chat_id', '')
        
        # Get new data refresh and auto-generation settings
        pnl_refresh_interval = request.POST.get('pnl_refresh_interval', '5min')
        telegram_alert_interval = request.POST.get('telegram_alert_interval', '15min')
        enable_eod_summary = 'enable_eod_summary' in request.POST
        
        # Get alert preferences
        enable_target_alerts = 'enable_target_alerts' in request.POST
        enable_stoploss_alerts = 'enable_stoploss_alerts' in request.POST
        auto_close_targets = 'auto_close_targets' in request.POST
        auto_close_stoploss = 'auto_close_stoploss' in request.POST
        enable_trade_alerts = 'enable_trade_alerts' in request.POST
        enable_bulk_alerts = 'enable_bulk_alerts' in request.POST
        enable_summary_alerts = 'enable_summary_alerts' in request.POST
        
        # Get lot size configuration
        nifty_lot_size = int(request.POST.get('nifty_lot_size', 75))
        banknifty_lot_size = int(request.POST.get('banknifty_lot_size', 35))
        
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
            
            # Alert preferences
            'enable_target_alerts': enable_target_alerts,
            'enable_stoploss_alerts': enable_stoploss_alerts,
            'auto_close_targets': auto_close_targets,
            'auto_close_stoploss': auto_close_stoploss,
            'enable_trade_alerts': enable_trade_alerts,
            'enable_bulk_alerts': enable_bulk_alerts,
            'enable_summary_alerts': enable_summary_alerts,
            
            # Lot size configuration
            'nifty_lot_size': nifty_lot_size,
            'banknifty_lot_size': banknifty_lot_size,
        })
        
        try:
            utils.save_settings(current_settings)
            messages.success(request, 'Settings updated successfully! All preferences have been saved.')
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')
        
        return redirect('settings')

    # Load current settings for display
    current_settings = utils.load_settings()
    
    context = {
        'settings': current_settings,
        'choices': choices,
        'weekdays': weekdays
    }
    return render(request, 'analyzer/settings.html', context)


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
                    'auto_add_portfolio': 'auto_add_portfolio' in request.POST,
                    'created_at': datetime.now().isoformat(),
                    'last_run': None,
                    'last_result': None,
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
                        'auto_add_portfolio': 'auto_add_portfolio' in request.POST,
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
                    
            elif action == 'get_recent_activities':
                # Get recent automation activities
                activities = utils.get_recent_automation_activities(limit=10)
                return JsonResponse({'success': True, 'activities': activities})
                
            elif action == 'simulate_automation':
                # Simulate automation completion for testing notifications
                import random
                instruments = ['NIFTY', 'BANKNIFTY']
                selected_instrument = random.choice(instruments)
                
                utils.add_automation_activity(
                    'Charts Generated', 
                    f'{selected_instrument} charts generated successfully via automation',
                    'success'
                )
                
                return JsonResponse({
                    'success': True, 
                    'message': f'Simulated {selected_instrument} automation completion'
                })
                    
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
    
    context = {
        'multiple_schedules': multiple_schedules,
        'weekdays': weekdays,
        'settings': current_settings,
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
    closed_trades = [t for t in all_trades if t.get('status') in ['Target', 'Stoploss', 'Manually Closed']]
    
    # Apply filters
    status_filter = request.GET.get('status_filter', '')
    instrument_filter = request.GET.get('instrument_filter', '')
    tag_filter = request.GET.get('tag_filter', '')
    
    if status_filter:
        closed_trades = [t for t in closed_trades if t.get('status') == status_filter]
    
    if instrument_filter:
        closed_trades = [t for t in closed_trades if t.get('instrument') == instrument_filter]
    
    if tag_filter:
        closed_trades = [t for t in closed_trades if t.get('entry_tag') == tag_filter]
    
    # Calculate statistics
    total_profit = sum(t.get('final_pnl', 0) for t in closed_trades if t.get('final_pnl', 0) > 0)
    total_loss = abs(sum(t.get('final_pnl', 0) for t in closed_trades if t.get('final_pnl', 0) < 0))
    net_pnl = total_profit - total_loss
    
    profitable_trades = len([t for t in closed_trades if t.get('final_pnl', 0) > 0])
    total_closed = len(closed_trades)
    win_rate = (profitable_trades / total_closed * 100) if total_closed > 0 else 0
    
    # Get available tags for filter dropdown
    available_tags = list(set(t.get('entry_tag', 'General') for t in all_trades if t.get('entry_tag')))
    available_tags = sorted([tag for tag in available_tags if tag])
    
    # Fix missing data for existing closed trades
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
                # Calculate P&L based on initial premium and current market data
                try:
                    lot_size = utils.get_lot_size(trade.get('instrument', 'NIFTY'))
                    initial_premium = trade.get('initial_premium', 0)
                    
                    # For closed trades, we'll estimate final P&L as 0 if we can't calculate it
                    # This is because we don't have the closing premium data
                    trade['final_pnl'] = 0
                    
                    # If it's a target hit, estimate positive P&L
                    if trade.get('status') == 'Target':
                        target_amount = trade.get('target_amount', 0)
                        if target_amount > 0:
                            trade['final_pnl'] = target_amount
                    # If it's a stoploss hit, estimate negative P&L
                    elif trade.get('status') == 'Stoploss':
                        stoploss_amount = trade.get('stoploss_amount', 0)
                        if stoploss_amount > 0:
                            trade['final_pnl'] = -stoploss_amount
                except:
                    trade['final_pnl'] = 0
    
    context = {
        'closed_trades': closed_trades,
        'total_profit': total_profit,
        'total_loss': total_loss,
        'net_pnl': net_pnl,
        'win_rate': win_rate,
        'status_filter': status_filter,
        'instrument_filter': instrument_filter,
        'tag_filter': tag_filter,
        'available_tags': available_tags,
    }
    
    return render(request, 'analyzer/closed_trades.html', context)
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
                # Calculate P&L based on initial premium and current market data
                try:
                    lot_size = utils.get_lot_size(trade.get('instrument', 'NIFTY'))
                    initial_premium = trade.get('initial_premium', 0)
                    
                    # For closed trades, we'll estimate final P&L as 0 if we can't calculate it
                    # This is because we don't have the closing premium data
                    trade['final_pnl'] = 0
                    
                    # If it's a target hit, estimate positive P&L
                    if trade.get('status') == 'Target':
                        target_amount = trade.get('target_amount', 0)
                        if target_amount > 0:
                            trade['final_pnl'] = target_amount
                    # If it's a stoploss hit, estimate negative P&L
                    elif trade.get('status') == 'Stoploss':
                        stoploss_amount = trade.get('stoploss_amount', 0)
                        if stoploss_amount > 0:
                            trade['final_pnl'] = -stoploss_amount
                except:
                    trade['final_pnl'] = 0
    
    context = {
        'closed_trades': closed_trades,
        'total_profit': total_profit,
        'total_loss': total_loss,
        'net_pnl': net_pnl,
        'win_rate': win_rate,
        'status_filter': status_filter,
        'instrument_filter': instrument_filter,
        'tag_filter': tag_filter,
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