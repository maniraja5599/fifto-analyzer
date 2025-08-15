import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf
import math
import time
from datetime import datetime
import gradio as gr
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import pytz
from collections import defaultdict
import numpy as np
import uuid

# --- Configuration ---
BOT_TOKEN = "7476365992:AAGjDcQcMB7lkiy92VoDnZwixatakhe02DISUM"
CHAT_ID = "-1002886512293"
BASE_DIR = os.path.expanduser('~')
TRADES_DB_FILE = os.path.join(BASE_DIR, "active_trades.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "app_settings.json")


# --- Settings Management ---
def load_settings():
    """Loads settings from the settings file, providing defaults if it doesn't exist."""
    defaults = {"update_interval": "15 Mins"}
    if not os.path.exists(SETTINGS_FILE):
        return defaults
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return defaults

def save_settings(settings):
    """Saves the given settings dictionary to the settings file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)


# --- Helper & Data Functions ---

def load_trades():
    if not os.path.exists(TRADES_DB_FILE): return []
    try:
        with open(TRADES_DB_FILE, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_trades(trades):
    with open(TRADES_DB_FILE, 'w') as f:
        json.dump(trades, f, indent=4)

def get_option_chain_data(symbol):
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36', 'Accept': 'application/json, text/javascript, */*; q=0.01', 'Accept-Language': 'en-US,en;q=0.9'}
    api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    try:
        session.get(f"https://www.nseindia.com/get-quotes/derivatives?symbol={symbol}", headers=headers, timeout=15)
        time.sleep(1)
        response = session.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching option chain for {symbol}: {e}")
        return None

def send_telegram_message(message, image_paths=None):
    if BOT_TOKEN == "YOUR_BOT_TOKEN" or CHAT_ID == "YOUR_CHAT_ID": return "Telegram credentials not set."
    try:
        if image_paths:
            if isinstance(image_paths, str):
                image_paths = [image_paths]

            if len(image_paths) > 1:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup"
                files = {}
                media = []
                for i, path in enumerate(image_paths):
                    file_name = os.path.basename(path)
                    files[file_name] = open(path, 'rb')
                    photo_media = {'type': 'photo', 'media': f'attach://{file_name}'}
                    if i == 0 and message:
                        photo_media['caption'] = message
                    media.append(photo_media)
                
                response = requests.post(url, data={'chat_id': CHAT_ID, 'media': json.dumps(media)}, files=files)
                for f in files.values():
                    f.close()
            elif len(image_paths) == 1:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                with open(image_paths[0], 'rb') as img:
                    response = requests.post(url, data={'chat_id': CHAT_ID, 'caption': message}, files={'photo': img})
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            response = requests.post(url, data={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'})
            
        response.raise_for_status()
        return "Message sent to Telegram."
    except requests.exceptions.RequestException as e:
        return f"Failed to send to Telegram: {e}"

# --- Charting Functions ---

def generate_pl_update_image(data_for_image, timestamp):
    """Generates an image from P/L data with a light color theme and timestamp."""
    num_lines = 1 + sum(len(trades) + 1.5 for _, trades in data_for_image['tags'].items())
    fig_height = max(3, num_lines * 0.4)
    
    fig, ax = plt.subplots(figsize=(8, fig_height), facecolor='#F4F6F6')
    ax.axis('off')

    fig.text(0.5, 0.95, data_for_image['title'], ha='center', va='top', fontsize=18, fontweight='bold', color='#17202A')

    y_pos = 0.85
    line_height = 1.0 / (num_lines + 2)

    for tag, trades in sorted(data_for_image['tags'].items()):
        ax.text(0.1, y_pos, f"{tag}", ha='left', va='top', fontsize=14, fontweight='bold', color='#2980B9')
        y_pos -= line_height * 1.2

        for trade in trades:
            reward_type = trade['reward_type']
            pnl = trade['pnl']
            pnl_color = '#27AE60' if pnl >= 0 else '#C0392B'
            
            ax.text(0.15, y_pos, f"• {reward_type}:", ha='left', va='top', fontsize=13, color='#212F3D')
            ax.text(0.85, y_pos, f"₹{pnl:,.2f}", ha='right', va='top', fontsize=13, color=pnl_color, family='monospace', weight='bold')
            y_pos -= line_height
        
        y_pos -= (line_height / 2)

    # Add timestamp
    timestamp_str = timestamp.strftime("%d-%b-%Y %I:%M:%S %p")
    fig.text(0.98, 0.02, timestamp_str, ha='right', va='bottom', fontsize=9, color='#566573')

    filename = f"pl_update_{uuid.uuid4().hex}.png"
    filepath = os.path.join(os.path.expanduser('~'), filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor(), pad_inches=0.1)
    plt.close(fig)
    return filepath

def generate_payoff_chart(strategies_df, lot_size, current_price, instrument_name, zone_label, expiry_label):
    """Generates the payoff chart with shaded P/L zones and max profit annotation."""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    price_range = np.linspace(current_price * 0.90, current_price * 1.10, 500)
    
    for strategy in strategies_df.to_dict('records'):
        if strategy['Entry'] == 'High Reward':
            ce_strike = strategy['CE Strike']
            pe_strike = strategy['PE Strike']
            premium = strategy['Combined Premium'] 
            
            pnl = (premium - np.maximum(price_range - ce_strike, 0) - np.maximum(pe_strike - price_range, 0)) * lot_size
            ax.plot(price_range, pnl, label="Payoff", linewidth=2.5)

            be_upper = ce_strike + premium
            be_lower = pe_strike - premium
            max_profit = premium * lot_size
            
            ax.fill_between(price_range, pnl, 0, where=(pnl >= 0), facecolor='green', alpha=0.3, interpolate=True, label='Profit')
            ax.fill_between(price_range, pnl, 0, where=(pnl <= 0), facecolor='red', alpha=0.3, interpolate=True, label='Loss')

            ax.axvline(x=be_lower, color='grey', linestyle='--', label=f'Lower BEP: {be_lower:,.0f}')
            ax.axvline(x=be_upper, color='grey', linestyle='--', label=f'Upper BEP: {be_upper:,.0f}')
            
            ax.annotate(f'Max Profit: ₹{max_profit:,.2f}',
                        xy=(current_price, max_profit),
                        xytext=(current_price, max_profit * 0.5),
                        ha='center', va='center', fontsize=11, fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.5", fc="lightgreen", alpha=0.9))
            break

    ax.set_title(f"Payoff Graph for Expiry: {expiry_label}", fontsize=14)
    fig.suptitle(f"FiFTO {zone_label} Selling - {instrument_name}", fontsize=16, fontweight='bold')
    ax.axhline(y=0, color='black', linestyle='-', lw=1.0)
    ax.set_xlabel("Stock Price at Expiration", fontsize=12)
    ax.set_ylabel("Profit / Loss (₹)", fontsize=12)
    ax.set_ylim(-25000, 25000)
    ax.legend()
    
    chart_gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fig.text(0.99, 0.01, f'Generated: {chart_gen_time}', horizontalalignment='right', verticalalignment='bottom', fontsize=8, color='gray')

    filename = f"payoff_{uuid.uuid4().hex}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return filename

def generate_analysis(instrument_name, calculation_type, selected_expiry_str, progress=None):
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    
    if not all([instrument_name, calculation_type, selected_expiry_str]) or "Error" in selected_expiry_str:
        return None, None, "Please select valid inputs.", None, None, None

    if progress: progress(0.1, desc="Initializing..."); 
    ticker_symbol = TICKERS[instrument_name]
    
    lot_size = 75 if instrument_name == "NIFTY" else 15
    strike_increment = 50 if instrument_name == "NIFTY" else 100
        
    if progress: progress(0.2, desc=f"Calculating {calculation_type} zones...");
    
    # EXACT ORIGINAL NIFSEL.py LOGIC
    print(f"🔄 ORIGINAL NIFSEL.py: Calculating {calculation_type} zones for {instrument_name}...")
    df_zones = yf.Ticker(ticker_symbol).history(period="5y", interval="1d")
    if calculation_type == "Weekly" and instrument_name == "NIFTY":
        df_zones = yf.Ticker(ticker_symbol).history(period="6mo", interval="1d")
        print(f"📅 ORIGINAL NIFSEL.py: Using 6mo period for Weekly NIFTY")
    else:
        print(f"📅 ORIGINAL NIFSEL.py: Using 5y period for {calculation_type} {instrument_name}")
    
    if df_zones.empty: 
        return None, None, f"Failed to calculate zones.", None, None, None
    
    print(f"✅ Got {len(df_zones)} days of data from yfinance")
    
    df_zones.index = pd.to_datetime(df_zones.index)
    resample_period = 'W' if calculation_type == "Weekly" else 'ME'
    
    print(f"📊 ORIGINAL NIFSEL.py: Resampling to {resample_period}")
    agg_df = df_zones.resample(resample_period).agg({'Open': 'first', 'High': 'max', 'Low': 'min'}).dropna()
    print(f"✅ Resampled to {len(agg_df)} periods")
    
    rng5, rng10 = (agg_df['High'] - agg_df['Low']).rolling(5).mean(), (agg_df['High'] - agg_df['Low']).rolling(10).mean()
    base = agg_df['Open']
    u1, u2 = base + 0.5 * rng5, base + 0.5 * rng10
    l1, l2 = base - 0.5 * rng5, base - 0.5 * rng10
    latest_zones = pd.DataFrame({'u1': u1, 'u2': u2, 'l1': l1, 'l2': l2}).dropna().iloc[-1]
    supply_zone, demand_zone = round(max(latest_zones['u1'], latest_zones['u2']), 2), round(min(latest_zones['l1'], latest_zones['l2']), 2)
    
    print(f"✅ ORIGINAL NIFSEL.py zones calculated:")
    print(f"   Latest Base (Open): ₹{base.iloc[-1]:.2f}")
    print(f"   RNG5 (5-period SMA): ₹{rng5.iloc[-1]:.2f}")
    print(f"   RNG10 (10-period SMA): ₹{rng10.iloc[-1]:.2f}")
    print(f"   Supply Zone: ₹{supply_zone}")
    print(f"   Demand Zone: ₹{demand_zone}")
    print(f"   Zone Range: ₹{supply_zone - demand_zone:.2f}")
    
    zone_label = calculation_type
    
    if progress: progress(0.4, desc="Fetching option chain..."); 
    option_chain_data = get_option_chain_data(instrument_name)
    if not option_chain_data: return None, None, f"Error fetching option chain.", None, None, None

    current_price = option_chain_data['records']['underlyingValue']; expiry_label = datetime.strptime(selected_expiry_str, '%d-%b-%Y').strftime("%d-%b")

    if progress: progress(0.6, desc="Parsing data..."); 
    ce_prices, pe_prices = {}, {}
    for item in option_chain_data['records']['data']:
        if item.get("expiryDate") == selected_expiry_str:
            if item.get("CE"): ce_prices[item['strikePrice']] = item["CE"]["lastPrice"]
            if item.get("PE"): pe_prices[item['strikePrice']] = item["PE"]["lastPrice"]

    ce_high = math.ceil(supply_zone / strike_increment) * strike_increment; strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
    pe_high = math.floor(demand_zone / strike_increment) * strike_increment
    candidate_puts = sorted([s for s in pe_prices if s < pe_high and pe_prices.get(s, 0) > 0], key=lambda s: pe_prices.get(s, 0), reverse=True)
    pe_mid, pe_low = (candidate_puts[0] if candidate_puts else pe_high - strike_increment), (candidate_puts[1] if len(candidate_puts) > 1 else (candidate_puts[0] if candidate_puts else pe_high - strike_increment) - strike_increment)
    strikes_pe = [pe_high, pe_mid, pe_low]

    if progress: progress(0.8, desc="Creating charts...");
    df = pd.DataFrame({"Entry": ["High Reward", "Mid Reward", "Low Reward"], "CE Strike": strikes_ce, "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce], "PE Strike": strikes_pe, "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe]})
    df["Combined Premium"] = df["CE Price"] + df["PE Price"]
    df["Target"] = (df["Combined Premium"] * 0.80 * lot_size).round(2)
    df["Stoploss"] = (df["Combined Premium"] * 0.80 * lot_size).round(2)
    display_df = df[['Entry', 'CE Strike', 'CE Price', 'PE Strike', 'PE Price']].copy()
    display_df['Target/SL (1:1)'] = df['Target']

    title, summary_filename = f"FiFTO - {zone_label} {instrument_name} Selling", f"{instrument_name}_{zone_label}_Summary.png"
    fig, ax = plt.subplots(figsize=(10, 5)); fig.patch.set_facecolor('#e0f7fa'); ax.axis('off')
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    chart_gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info_text = f"{instrument_name}: {current_price}\nExpiry: {expiry_label}\nGenerated: {chart_gen_time}"
    ax.text(0.5, 0.85, info_text, transform=ax.transAxes, ha='center', va='center', fontsize=12, family='monospace')
    table_colors = ['#00acc1'] * len(display_df.columns)
    table = plt.table(cellText=display_df.values, colLabels=display_df.columns, colColours=table_colors, cellLoc='center', loc='center')
    table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1.2, 2)
    for (row, col), cell in table.get_celld().items():
        if row == 0: cell.get_text().set_color('white')
    
    disclaimer_text = ("Disclaimer: We are not SEBI registered advisors. All views are personal and for educational purposes only.\n"
                       "Please consult a financial advisor before investing.")
    fig.text(0.5, 0.01, disclaimer_text, ha='center', va='bottom', fontsize=7, color='grey', style='italic')

    plt.savefig(summary_filename, dpi=300, bbox_inches='tight'); plt.close(fig)

    payoff_filename = generate_payoff_chart(df, lot_size, current_price, instrument_name, zone_label, expiry_label)
    
    analysis_data = {"instrument": instrument_name, "expiry": selected_expiry_str, "lot_size": lot_size, "df_data": df.to_dict('records')}
    return summary_filename, payoff_filename, f"Charts generated for {instrument_name}.", analysis_data, summary_filename, payoff_filename

# --- Trade Management & Monitoring ---

def add_to_analysis(analysis_data):
    if not analysis_data or not analysis_data['df_data']: return "Generate an analysis first.", gr.DataFrame(value=load_trades_for_display())
    trades = load_trades()
    new_trades_added = 0
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = days[datetime.now().weekday()]
    entry_tag = f"{day_name} Selling"

    for entry in analysis_data['df_data']:
        trade_id = f"{analysis_data['instrument']}_{analysis_data['expiry']}_{entry['Entry'].replace(' ', '')}"
        if any(t['id'] == trade_id for t in trades): continue
        trades.append({"id": trade_id, "start_time": start_time, "instrument": analysis_data['instrument'], "expiry": analysis_data['expiry'], "reward_type": entry['Entry'], "ce_strike": entry['CE Strike'], "pe_strike": entry['PE Strike'], "initial_premium": entry['Combined Premium'], "target_amount": entry['Target'], "stoploss_amount": entry['Stoploss'], "status": "Running", "entry_tag": entry_tag})
        new_trades_added += 1
    save_trades(trades)
    return f"Added {new_trades_added} new trade(s) tagged as '{entry_tag}'.", gr.DataFrame(value=load_trades_for_display())

def load_trades_for_display():
    trades = load_trades()
    if not trades: return pd.DataFrame(columns=["ID", "Tag", "Start Time", "Status", "Initial Amount (₹)", "Target Profit (₹)", "Stoploss (₹)"])
    df = pd.DataFrame(trades)
    df['lot_size'] = df['instrument'].apply(lambda x: 75 if x == 'NIFTY' else 15)
    df['initial_amount'] = (df['initial_premium'] * df['lot_size']).round()
    if 'start_time' not in df.columns: df['start_time'] = 'N/A'
    if 'entry_tag' not in df.columns: df['entry_tag'] = 'N/A'
    display_df = df[['id', 'entry_tag', 'start_time', 'status', 'initial_amount', 'target_amount', 'stoploss_amount']].copy()
    display_df.rename(columns={'id': 'ID', 'entry_tag': 'Tag', 'start_time': 'Start Time', 'status': 'Status', 'initial_amount': 'Initial Amount (₹)', 'target_amount': 'Target Profit (₹)', 'stoploss_amount': 'Stoploss (₹)'}, inplace=True)
    return display_df

def close_selected_trade(trades_df, selected_index):
    if selected_index is None or not isinstance(selected_index, int) or trades_df.empty: return trades_df, "Please select a trade to close first.", None
    trade_id_to_close = trades_df.iloc[selected_index]['ID']
    all_trades = load_trades()
    trade_to_close = next((t for t in all_trades if t['id'] == trade_id_to_close), None)
    if not trade_to_close: return load_trades_for_display(), f"Error: Trade with ID {trade_id_to_close} not found.", None
    instrument = trade_to_close['instrument']
    chain = get_option_chain_data(instrument)
    current_ce, current_pe = 0.0, 0.0
    if chain:
        for item in chain['records']['data']:
            if item['expiryDate'] == trade_to_close['expiry']:
                if item['strikePrice'] == trade_to_close['ce_strike'] and item.get('CE'): current_ce = item['CE']['lastPrice']
                if item['strikePrice'] == trade_to_close['pe_strike'] and item.get('PE'): current_pe = item['PE']['lastPrice']
    combined_price = current_ce + current_pe
    message = (f"🔔 *Manual Square-Off Alert* 🔔\n\n"
               f"Please square-off the following position:\n"
               f"*- Tag:* `{trade_to_close.get('entry_tag', 'N/A')}`\n"
               f"*- Trade:* `{trade_to_close['id']}`\n\n"
               f"*Current Market Price:*\n"
               f"*- CE Price:* `₹{current_ce:.2f}`\n"
               f"*- PE Price:* `₹{current_pe:.2f}`\n"
               f"*- Combined:* `₹{combined_price:.2f}`")
    send_telegram_message(message)
    remaining_trades = [t for t in all_trades if t['id'] != trade_id_to_close]
    save_trades(remaining_trades)
    return load_trades_for_display(), f"Square-off alert for {trade_id_to_close} sent to Telegram.", None

def monitor_trades(is_eod_report=False):
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    print(f"[{now}] Running trade monitoring...")
    trades = load_trades()
    if not trades: return
    
    active_trades, completed_trades = [], []
    for t in trades:
        if t['status'] == 'Running' and datetime.strptime(t['expiry'], '%d-%b-%Y').date() >= now.date(): active_trades.append(t)
        else: completed_trades.append(t)

    trade_groups = defaultdict(lambda: defaultdict(list))
    for trade in active_trades:
        group_key = f"{trade['instrument']}_{trade['expiry']}"
        entry_tag = trade.get('entry_tag', 'General Trades')
        trade_groups[group_key][entry_tag].append(trade)
    
    eod_summary_data = []
    
    for group_key, tagged_trades in trade_groups.items():
        instrument, expiry = group_key.split('_')
        chain = get_option_chain_data(instrument)
        if not chain: continue
        lot_size = 75 if instrument == "NIFTY" else 15
        
        pl_data_for_image = {'title': f"{instrument} {expiry} P/L Update", 'tags': defaultdict(list)}
        any_trade_updated = False

        for tag, trades_in_group in sorted(tagged_trades.items()):
            for trade in trades_in_group:
                current_ce, current_pe = 0.0, 0.0
                for item in chain['records']['data']:
                    if item['expiryDate'] == trade['expiry']:
                        if item['strikePrice'] == trade['ce_strike'] and item.get('CE'): current_ce = item['CE']['lastPrice']
                        if item['strikePrice'] == trade['pe_strike'] and item.get('PE'): current_pe = item['PE']['lastPrice']
                
                if current_ce == 0.0 and current_pe == 0.0: continue
                
                pnl = (trade['initial_premium'] - (current_ce + current_pe)) * lot_size
                any_trade_updated = True
                
                if is_eod_report:
                    eod_summary_data.append(f"-> {trade['id']}: Current P/L: ₹{pnl:.2f}")
                else:
                    pl_data_for_image['tags'][tag].append({'reward_type': trade['reward_type'], 'pnl': pnl})
                    if pnl >= trade['target_amount']:
                        trade['status'] = 'Target'; msg = f"✅ TARGET HIT: {trade['id']} ({tag})\nP/L: ₹{pnl:.2f}"
                        print(msg); send_telegram_message(msg)
                    elif pnl <= -trade['stoploss_amount']:
                        trade['status'] = 'Stoploss'; msg = f"❌ STOPLOSS HIT: {trade['id']} ({tag})\nP/L: ₹{pnl:.2f}"
                        print(msg); send_telegram_message(msg)

        if not is_eod_report and any_trade_updated:
            image_path = generate_pl_update_image(pl_data_for_image, now)
            send_telegram_message(message="", image_paths=[image_path])
            os.remove(image_path)
    
    if is_eod_report and eod_summary_data:
        eod_message = f"--- EOD Summary ({now.strftime('%d-%b-%Y %I:%M %p')}) ---\n" + "\n".join(eod_summary_data)
        send_telegram_message(eod_message)
        
    save_trades(active_trades + completed_trades)

# --- UI & App Lifecycle ---

def update_expiry_dates(index_name):
    """Restored function to update expiry dates dropdown."""
    data = get_option_chain_data(index_name)
    if data and 'records' in data and 'expiryDates' in data['records']:
        future_expiries = sorted([d for d in data['records']['expiryDates'] if datetime.strptime(d, "%d-%b-%Y").date() >= datetime.now().date()], key=lambda x: datetime.strptime(x, "%d-%b-%Y"))
        return gr.Dropdown(choices=future_expiries, value=future_expiries[0] if future_expiries else None, interactive=True)
    return gr.Dropdown(choices=["Error"], value="Error", interactive=False)

def update_monitoring_interval(interval_str, scheduler):
    """Reschedules or pauses the trade monitoring job."""
    try:
        if interval_str == "Disable":
            scheduler.pause_job('pl_monitor')
            msg = "P/L monitoring has been disabled."
        else:
            value, unit = interval_str.split()
            value = int(value)
            if unit == 'Mins': scheduler.reschedule_job('pl_monitor', trigger='interval', minutes=value)
            elif unit == 'Hour': scheduler.reschedule_job('pl_monitor', trigger='interval', hours=value)
            scheduler.resume_job('pl_monitor')
            msg = f"P/L update interval set to {interval_str}."
        
        current_settings = load_settings()
        current_settings['update_interval'] = interval_str
        save_settings(current_settings)
        print(msg)
        return msg
    except Exception as e:
        error_msg = f"Failed to update schedule: {e}"; print(error_msg); return error_msg

def send_daily_chart_to_telegram(summary_path, payoff_path, analysis_data):
    """Creates a dynamic message title for manual chart sends."""
    if not summary_path or not payoff_path or not analysis_data:
        return "Generate charts first."

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = days[datetime.now().weekday()]
    
    if day_name in ["Friday", "Monday"]:
        title = f"📊 **{day_name} Selling Summary**"
    else:
        title = "📊 **Chart Summary**"
    
    lot_size = analysis_data['lot_size']
    message_lines = [title]
    for entry in analysis_data['df_data']:
        amount = entry['Combined Premium'] * lot_size
        message_lines.append(f"- {entry['Entry']} Reward: ₹{amount:.2f}")
    
    full_message = "\n".join(message_lines)
    send_telegram_message(full_message, image_paths=[summary_path, payoff_path])
    return "Message sent to Telegram."

def build_ui(scheduler):
    with gr.Blocks(theme=gr.themes.Default(), title="FiFTO Analyzer") as demo:
        gr.Markdown("# FiFTO WEEKLY SELLING")
        
        analysis_data_state = gr.State()
        summary_filepath_state = gr.State()
        payoff_filepath_state = gr.State()
        selected_trade_state = gr.State()

        with gr.Tabs():
            with gr.TabItem("Trade Generator"):
                with gr.Group():
                    with gr.Row():
                        index_dropdown = gr.Dropdown(choices=["NIFTY", "BANKNIFTY"], label="Select Index", value="NIFTY")
                        calc_dropdown = gr.Dropdown(choices=["Weekly", "Monthly"], label="Select Calculation Type", value="Weekly")
                        expiry_dropdown = gr.Dropdown(label="Select Expiry Date", info="Loading...", interactive=False)
                    with gr.Row():
                        run_button = gr.Button("Generate Charts", variant="primary"); reset_button = gr.Button("Reset / Stop")
                
                status_textbox_gen = gr.Textbox(label="Status", interactive=False)
                
                with gr.Tabs() as output_tabs:
                    with gr.TabItem("Analysis Chart"):
                        output_summary_image = gr.Image(show_label=False)
                    with gr.TabItem("Payoff Chart"):
                        output_payoff_image = gr.Image(show_label=False)

                with gr.Row():
                    add_button = gr.Button("Add to Analysis"); telegram_button = gr.Button("Send to Telegram")

            with gr.TabItem("Active Analysis"):
                gr.Markdown("First, **click a row** to select it. Then, click the 'Close Selected Trade' button.")
                analysis_df = gr.DataFrame(load_trades_for_display, label="Monitored Trades", interactive=True)
                with gr.Row():
                    close_button = gr.Button("Close Selected Trade"); refresh_button = gr.Button("Refresh List")

            with gr.TabItem("Settings"):
                gr.Markdown("## P/L Monitoring Settings\nControl how often the application checks for P/L updates and sends notifications to Telegram.")
                settings_interval = gr.Radio(choices=['15 Mins', '30 Mins', '1 Hour', 'Disable'], label="Telegram P/L Update Frequency", value=lambda: load_settings()['update_interval'])
                save_settings_button = gr.Button("Save Settings", variant="primary")
                settings_status = gr.Textbox(label="Status", interactive=False)

        # Event Listeners
        run_event = run_button.click(fn=generate_analysis, inputs=[index_dropdown, calc_dropdown, expiry_dropdown], outputs=[output_summary_image, output_payoff_image, status_textbox_gen, analysis_data_state, summary_filepath_state, payoff_filepath_state])
        add_button.click(fn=add_to_analysis, inputs=[analysis_data_state], outputs=[status_textbox_gen, analysis_df])
        
        telegram_button.click(
            fn=send_daily_chart_to_telegram, 
            inputs=[summary_filepath_state, payoff_filepath_state, analysis_data_state], 
            outputs=[status_textbox_gen]
        )
        
        def reset_ui(): return None, None, "Process stopped.", None, None, None
        reset_button.click(fn=reset_ui, inputs=[], outputs=[output_summary_image, output_payoff_image, status_textbox_gen, analysis_data_state, summary_filepath_state, payoff_filepath_state], cancels=[run_event])

        def store_selection(evt: gr.SelectData): return evt.index[0] if evt.index else None
        analysis_df.select(fn=store_selection, inputs=None, outputs=[selected_trade_state])
        close_button.click(fn=close_selected_trade, inputs=[analysis_df, selected_trade_state], outputs=[analysis_df, status_textbox_gen, selected_trade_state])
        refresh_button.click(fn=load_trades_for_display, outputs=[analysis_df])
        
        index_dropdown.change(fn=update_expiry_dates, inputs=index_dropdown, outputs=expiry_dropdown)
        
        save_settings_button.click(fn=lambda interval: update_monitoring_interval(interval, scheduler), inputs=[settings_interval], outputs=[settings_status])
        demo.load(fn=update_expiry_dates, inputs=index_dropdown, outputs=expiry_dropdown)
        
    return demo

if __name__ == "__main__":
    app_settings = load_settings()
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
    
    interval_str = app_settings.get("update_interval", "15 Mins")
    job_kwargs = {}
    is_paused = False
    if interval_str == "Disable":
        is_paused = True
        job_kwargs['minutes'] = 15
    else:
        value, unit = interval_str.split()
        value = int(value)
        if unit == 'Mins': job_kwargs['minutes'] = value
        elif unit == 'Hour': job_kwargs['hours'] = value
            
    scheduler.add_job(monitor_trades, 'interval', **job_kwargs, args=[False], id='pl_monitor')
    scheduler.add_job(lambda: monitor_trades(is_eod_report=True), 'cron', day_of_week='mon-fri', hour=15, minute=45, id='eod_report')
    
    scheduler.start()
    if is_paused: scheduler.pause_job('pl_monitor')

    atexit.register(lambda: scheduler.shutdown())
    
    demo = build_ui(scheduler)
    demo.queue(max_size=20).launch(inbrowser=True)  # Added queue() to fix the progress tracking issue