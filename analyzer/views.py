# analyzer/views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from . import utils
from datetime import datetime
import pandas as pd

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

    # This dictionary will hold the grouped trades
    batched_trades = defaultdict(list)
    total_pnl = 0

    nifty_chain = utils.get_option_chain_data("NIFTY")
    banknifty_chain = utils.get_option_chain_data("BANKNIFTY")

    for trade in trades:
        if trade['status'] != 'Running':
            continue

        # Calculate P&L for each trade
        chain_data = nifty_chain if trade['instrument'] == 'NIFTY' else banknifty_chain
        # ... (P&L calculation logic is the same as the previous version) ...
        # ... After calculating pnl ...

        trade['pnl'] = pnl
        total_pnl += pnl

        # Group the trade into its batch
        batch_key = trade.get('entry_tag', 'General Trades')
        batched_trades[batch_key].append(trade)

    context = {
        'batched_trades': dict(batched_trades), # Convert to regular dict for template
        'total_pnl': total_pnl
    }
    
    return render(request, 'analyzer/trades.html', context)
    trades = utils.load_trades()
    trades_with_pnl = []
    total_pnl = 0

    # Fetches live prices to calculate P&L
    nifty_chain = utils.get_option_chain_data("NIFTY")
    banknifty_chain = utils.get_option_chain_data("BANKNIFTY")

    for trade in trades:
        if trade['status'] != 'Running':
            continue

        # --- LOGIC TO ADD DATE TO TAG ---
        try:
            # Parse the start_time string
            start_dt = datetime.strptime(trade['start_time'], "%Y-%m-%d %H:%M")
            # Format the date and prepend it to the existing tag
            trade['entry_tag'] = f"{start_dt.strftime('%d-%b')} {trade.get('entry_tag', '')}"
        except (ValueError, KeyError):
            # If start_time is missing or in a wrong format, do nothing
            pass
        # ------------------------------------

        chain_data = nifty_chain if trade['instrument'] == 'NIFTY' else banknifty_chain
        current_ce, current_pe = 0.0, 0.0

        if chain_data and chain_data.get('records', {}).get('data'):
            for item in chain_data['records']['data']:
                if item.get("expiryDate") == trade['expiry']:
                    if item.get("strikePrice") == trade['ce_strike'] and item.get("CE"):
                        current_ce = item["CE"]["lastPrice"]
                    if item.get("strikePrice") == trade['pe_strike'] and item.get("PE"):
                        current_pe = item["PE"]["lastPrice"]

        lot_size = 75 if trade['instrument'] == 'NIFTY' else 15
        initial_premium = trade.get('initial_premium', 0)
        current_premium = current_ce + current_pe

        if current_premium > 0:
            pnl = (initial_premium - current_premium) * lot_size
            trade['pnl'] = pnl
            total_pnl += pnl
        else:
            trade['pnl'] = "N/A"

        trades_with_pnl.append(trade)

    context = {
        'trades': trades_with_pnl,
        'total_pnl': total_pnl
    }
    return render(request, 'analyzer/trades.html', context)
    trades = utils.load_trades()
    trades_with_pnl = []
    total_pnl = 0

    # Get current prices to calculate live P&L
    # This is a simplified approach; for many trades, optimize API calls
    nifty_chain = utils.get_option_chain_data("NIFTY")
    banknifty_chain = utils.get_option_chain_data("BANKNIFTY")

    for trade in trades:
        if trade['status'] != 'Running':
            continue

        chain_data = nifty_chain if trade['instrument'] == 'NIFTY' else banknifty_chain
        current_ce, current_pe = 0.0, 0.0

        if chain_data and chain_data.get('records', {}).get('data'):
            for item in chain_data['records']['data']:
                if item.get("expiryDate") == trade['expiry']:
                    if item.get("strikePrice") == trade['ce_strike'] and item.get("CE"):
                        current_ce = item["CE"]["lastPrice"]
                    if item.get("strikePrice") == trade['pe_strike'] and item.get("PE"):
                        current_pe = item["PE"]["lastPrice"]

        lot_size = 75 if trade['instrument'] == 'NIFTY' else 15
        initial_premium = trade.get('initial_premium', 0)
        current_premium = current_ce + current_pe

        if current_premium > 0: # Only calculate if we got a price
            pnl = (initial_premium - current_premium) * lot_size
            trade['pnl'] = pnl
            total_pnl += pnl
        else:
            trade['pnl'] = "N/A" # Could not fetch price

        trades_with_pnl.append(trade)

    context = {
        'trades': trades_with_pnl,
        'total_pnl': total_pnl
    }
    return render(request, 'analyzer/trades.html', context)


def settings_view(request):
    # The list of choices is now defined here in the Python code
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
    # Pass the new 'choices' list to the template
    context = {
        'settings': current_settings,
        'choices': choices
    }
    return render(request, 'analyzer/settings.html', context)
    if request.method == 'POST':
        current_settings = utils.load_settings()
        # Get data from all form fields
        current_settings['update_interval'] = request.POST.get('interval')
        current_settings['bot_token'] = request.POST.get('bot_token')
        current_settings['chat_id'] = request.POST.get('chat_id')

        utils.save_settings(current_settings)
        messages.success(request, 'Settings updated successfully. Restart the scheduler for changes to take effect.')
        return redirect(reverse('settings'))

    current_settings = utils.load_settings()
    return render(request, 'analyzer/settings.html', {'settings': current_settings})
    
def close_trade(request, trade_id):
    utils.close_selected_trade(trade_id)
    messages.success(request, f"Square-off alert for {trade_id} sent.")
    return redirect(reverse('trades_list'))


    # The list of choices is now defined here in the view
    choices = ['15 Mins', '30 Mins', '1 Hour', 'Disable']

    if request.method == 'POST':
        interval = request.POST.get('interval')
        current_settings = utils.load_settings()
        current_settings['update_interval'] = interval
        utils.save_settings(current_settings)
        messages.success(request, 'Settings updated successfully. Restart the scheduler for changes to take effect.')
        return redirect(reverse('settings'))

    current_settings = utils.load_settings()
    # Pass the choices list to the template
    context = {
        'settings': current_settings,
        'choices': choices
    }
    return render(request, 'analyzer/settings.html', context)

def send_charts(request):
    analysis_data = request.session.get('analysis_data')
    if not analysis_data:
        messages.warning(request, 'No analysis data found to send.')
        return redirect(reverse('index'))
    status = utils.send_daily_chart_to_telegram(analysis_data)
    messages.info(request, f"Telegram status: {status}")
    return redirect(reverse('index'))