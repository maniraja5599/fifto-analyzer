# analyzer/views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from . import utils
from datetime import datetime
import pandas as pd
from collections import defaultdict

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
    if request.method == 'POST':
        instrument = request.POST.get('instrument')
        calc_type = request.POST.get('calc_type')
        expiry = request.POST.get('expiry')
        analysis_data, status = utils.generate_analysis(instrument, calc_type, expiry)
        if analysis_data:
            request.session['analysis_data'] = analysis_data
            messages.success(request, status)
        else:
            messages.error(request, status)
    return redirect(reverse('index'))

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
        df['lot_size'] = df['instrument'].apply(lambda x: 75 if x == 'NIFTY' else 15)
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
    
    # Handle trade operations (delete, bulk delete)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete_trade':
            trade_id = request.POST.get('trade_id')
            trades = [t for t in trades if t['id'] != trade_id]
            utils.save_trades(trades)
            messages.success(request, f'Trade {trade_id} deleted successfully.')
            return redirect('trades_list')
            
        elif action == 'delete_batch':
            batch_tag = request.POST.get('batch_tag')
            original_count = len(trades)
            trades = [t for t in trades if t.get('entry_tag', 'General Trades') != batch_tag]
            deleted_count = original_count - len(trades)
            utils.save_trades(trades)
            messages.success(request, f'Deleted {deleted_count} trades from batch "{batch_tag}".')
            return redirect('trades_list')

    # Group trades by batch and calculate P&L
    batched_trades = defaultdict(list)
    total_pnl = 0
    
    # Get market data
    nifty_chain = utils.get_option_chain_data("NIFTY")
    banknifty_chain = utils.get_option_chain_data("BANKNIFTY")

    for trade in trades:
        if trade['status'] != 'Running':
            continue

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
        
        lot_size = 75 if trade['instrument'] == 'NIFTY' else 15
        initial_premium = trade.get('initial_premium', 0)
        current_premium = current_ce + current_pe
        
        if current_premium > 0:
            pnl = round((initial_premium - current_premium) * lot_size, 2)
            trade['pnl'] = pnl
            trade['current_premium'] = current_premium
            total_pnl += pnl
        else:
            trade['pnl'] = "N/A"
            trade['current_premium'] = "N/A"
        
        # Add to batch
        batch_key = trade.get('entry_tag', 'General Trades')
        batched_trades[batch_key].append(trade)

    # Calculate batch totals
    batch_summaries = {}
    for batch_tag, trades_in_batch in batched_trades.items():
        batch_pnl = sum(t['pnl'] for t in trades_in_batch if isinstance(t['pnl'], (int, float)))
        batch_summaries[batch_tag] = {
            'count': len(trades_in_batch),
            'total_pnl': batch_pnl,
            'trades': trades_in_batch
        }

    context = {
        'batch_summaries': batch_summaries,
        'total_pnl': total_pnl,
        'has_active_trades': len(batched_trades) > 0
    }

    return render(request, 'analyzer/trades.html', context)


def settings_view(request):
    choices = ['15 Mins', '30 Mins', '1 Hour', 'Disable']

    if request.method == 'POST':
        current_settings = utils.load_settings()
        current_settings['update_interval'] = request.POST.get('interval')
        current_settings['bot_token'] = request.POST.get('bot_token')
        current_settings['chat_id'] = request.POST.get('chat_id')

        utils.save_settings(current_settings)
        messages.success(request, 'Settings updated successfully. Restart the scheduler for changes to take effect.')
        return redirect(reverse('settings'))

    current_settings = utils.load_settings()
    context = {
        'settings': current_settings,
        'choices': choices
    }
    return render(request, 'analyzer/settings.html', context)


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