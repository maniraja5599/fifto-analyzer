# analyzer/views.py - Clean New Implementation

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
import json
import pandas as pd
from datetime import datetime
from collections import defaultdict
from . import utils
from .utils import generate_analysis, load_settings, save_settings

def index(request):
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
    analysis_data = request.session.get('analysis_data')
    if not analysis_data:
        messages.warning(request, 'No analysis data found to add trades.')
        return redirect(reverse('index'))
    status = utils.add_to_analysis(analysis_data)
    messages.success(request, status)
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
            if group_by == 'batch':
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
                utils.send_telegram_message(f"📝 Batch Close: {closed_count} trades from '{batch_tag}' closed with total P&L ₹{total_pnl:.2f}")
                messages.success(request, f'Closed {closed_count} trades from batch "{batch_tag}" with total P&L ₹{total_pnl:.2f}.')
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
            if group_by == 'batch':
                batch_tag = request.POST.get('batch_tag')
                original_count = len(trades)
                trades = [t for t in trades if t.get('entry_tag', 'General Trades') != batch_tag]
                deleted_count = original_count - len(trades)
                utils.save_trades(trades)
                # Send Telegram notification
                utils.send_telegram_message(f"🗑️ Batch Delete: {deleted_count} trades from '{batch_tag}' deleted")
                messages.success(request, f'Deleted {deleted_count} trades from batch "{batch_tag}".')
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
        
        # Group by batch or expiry
        if group_by == 'batch':
            group_key = trade.get('entry_tag', 'General Trades')
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
        'group_type_display': 'Batch' if group_by == 'batch' else 'Expiry Date',
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
    """Handle automation configuration for auto chart generation."""
    weekdays = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    ]

    if request.method == 'POST':
        # Auto-generation settings
        enable_auto_generation = 'enable_auto_generation' in request.POST
        auto_gen_days = request.POST.getlist('auto_gen_days')
        auto_gen_time = request.POST.get('auto_gen_time', '09:20')
        auto_gen_instruments = request.POST.getlist('auto_gen_instruments')
        nifty_calc_type = request.POST.get('nifty_calc_type', 'Weekly')
        banknifty_calc_type = request.POST.get('banknifty_calc_type', 'Monthly')
        
        # Load current settings and update automation settings
        current_settings = utils.load_settings()
        current_settings.update({
            # Auto-generation settings
            'enable_auto_generation': enable_auto_generation,
            'auto_gen_days': auto_gen_days,
            'auto_gen_time': auto_gen_time,
            'auto_gen_instruments': auto_gen_instruments,
            'nifty_calc_type': nifty_calc_type,
            'banknifty_calc_type': banknifty_calc_type,
        })
        
        try:
            utils.save_settings(current_settings)
            if enable_auto_generation:
                if auto_gen_instruments:
                    instrument_list = ', '.join([f"{inst} ({nifty_calc_type if inst == 'NIFTY' else banknifty_calc_type})" for inst in auto_gen_instruments])
                    messages.success(request, f'Automation enabled successfully! Charts will be generated for {instrument_list} as scheduled.')
                else:
                    messages.warning(request, 'Automation enabled but no instruments selected. Please select NIFTY and/or BANKNIFTY.')
            else:
                messages.info(request, 'Automation disabled. No automatic chart generation will occur.')
        except Exception as e:
            messages.error(request, f'Error saving automation settings: {str(e)}')
        
        return redirect('automation')

    # Load current settings for display
    current_settings = utils.load_settings()
    
    context = {
        'settings': current_settings,
        'weekdays': weekdays
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