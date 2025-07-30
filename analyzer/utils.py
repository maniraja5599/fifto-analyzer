# analyzer/utils.py

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf
import math, time, json, os, pytz, uuid
from datetime import datetime
from collections import defaultdict
import numpy as np
from django.conf import settings

# --- Configuration Paths ---
BASE_DIR_USER = os.path.expanduser('~') # User's home directory for data files
TRADES_DB_FILE = os.path.join(BASE_DIR_USER, "active_trades.json")
SETTINGS_FILE = os.path.join(BASE_DIR_USER, "app_settings.json")
STATIC_FOLDER_PATH = os.path.join(settings.BASE_DIR, 'static') # Django project's static folder

# --- Settings & Trade Management ---
def load_settings():
    """Loads settings, ensuring defaults for all keys exist."""
    defaults = {
        "update_interval": "15 Mins",
        "bot_token": "",
        "chat_id": ""
    }
    if not os.path.exists(SETTINGS_FILE):
        return defaults
    try:
        with open(SETTINGS_FILE, 'r') as f:
            loaded_settings = json.load(f)
            defaults.update(loaded_settings)
            return defaults
    except (json.JSONDecodeError, FileNotFoundError):
        return defaults

def save_settings(settings_data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings_data, f, indent=4)

def load_trades():
    if not os.path.exists(TRADES_DB_FILE): return []
    try:
        with open(TRADES_DB_FILE, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_trades(trades):
    with open(TRADES_DB_FILE, 'w') as f:
        json.dump(trades, f, indent=4)

# --- API and Charting Functions ---
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
        # Log error silently, return None to handle gracefully
        return None

def generate_pl_update_image(data_for_image, timestamp):
    """Generates a styled image from P/L data for Telegram updates."""
    num_lines = 1 + sum(len(trades) + 1.5 for _, trades in data_for_image['tags'].items())
    fig_height = max(3, num_lines * 0.4)

    fig, ax = plt.subplots(figsize=(8, fig_height), facecolor='#1e1e1e')
    ax.axis('off')

    fig.text(0.5, 0.95, data_for_image['title'], ha='center', va='top', fontsize=18, fontweight='bold', color='#f0f0f0')

    y_pos = 0.85
    line_height = 1.0 / (num_lines + 2)

    for tag, trades in sorted(data_for_image['tags'].items()):
        tag_pnl = sum(t['pnl'] for t in trades)
        tag_color = '#28a745' if tag_pnl >= 0 else '#dc3545'
        ax.text(0.1, y_pos, f"{tag}", ha='left', va='top', fontsize=14, fontweight='bold', color='#007bff')
        ax.text(0.9, y_pos, f"₹{tag_pnl:,.2f}", ha='right', va='top', fontsize=14, fontweight='bold', color=tag_color)
        y_pos -= line_height * 1.2

        for trade in trades:
            pnl = trade['pnl']
            pnl_color = '#28a745' if pnl >= 0 else '#dc3545'

            ax.text(0.15, y_pos, f"• {trade['reward_type']}:", ha='left', va='top', fontsize=13, color='#cccccc')
            ax.text(0.85, y_pos, f"₹{pnl:,.2f}", ha='right', va='top', fontsize=13, color=pnl_color, family='monospace')
            y_pos -= line_height

        y_pos -= (line_height / 2)

    timestamp_str = timestamp.strftime("%d-%b-%Y %I:%M:%S %p")
    fig.text(0.98, 0.02, timestamp_str, ha='right', va='bottom', fontsize=9, color='#888888')

    filename = f"pl_update_{uuid.uuid4().hex}.png"
    filepath = os.path.join(STATIC_FOLDER_PATH, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor(), pad_inches=0.1)
    plt.close(fig)
    return filepath
    app_settings = load_settings()
    bot_token = app_settings.get("bot_token")
    chat_id = app_settings.get("chat_id")

    if not bot_token or not chat_id:
        return "Telegram credentials are not configured in Settings."

    try:
        if image_paths:
            if isinstance(image_paths, str): image_paths = [image_paths]
            if len(image_paths) > 1:
                url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"
                files, media = {}, []
                for i, path in enumerate(image_paths):
                    file_name = os.path.basename(path)
                    files[file_name] = open(path, 'rb')
                    photo_media = {'type': 'photo', 'media': f'attach://{file_name}'}
                    if i == 0 and message: photo_media['caption'] = message
                    media.append(photo_media)
                response = requests.post(url, data={'chat_id': chat_id, 'media': json.dumps(media)}, files=files)
                for f in files.values(): f.close()
            elif len(image_paths) == 1:
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(image_paths[0], 'rb') as img:
                    response = requests.post(url, data={'chat_id': chat_id, 'caption': message}, files={'photo': img})
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, data={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'})
        response.raise_for_status()
        return "Message sent to Telegram."
    except requests.exceptions.RequestException as e:
        return f"Failed to send to Telegram: {e}"

def generate_payoff_chart(strategies_df, lot_size, current_price, instrument_name, zone_label, expiry_label):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    primary_color, text_color, grid_color = '#007bff', '#cccccc', '#444444'
    price_range = np.linspace(current_price * 0.90, current_price * 1.10, 500)
    strategy = strategies_df.iloc[0]
    ce_strike, pe_strike, premium = strategy['CE Strike'], strategy['PE Strike'], strategy['Combined Premium']
    pnl = (premium - np.maximum(price_range - ce_strike, 0) - np.maximum(pe_strike - price_range, 0)) * lot_size
    ax.plot(price_range, pnl, color=primary_color, linewidth=2.5, label="Payoff")
    ax.fill_between(price_range, pnl, 0, where=(pnl >= 0), color=primary_color, alpha=0.3, interpolate=True, label='Profit')
    ax.fill_between(price_range, pnl, 0, where=(pnl <= 0), color='#dc3545', alpha=0.3, interpolate=True, label='Loss')
    be_upper, be_lower = ce_strike + premium, pe_strike - premium
    ax.axhline(y=0, color=grid_color, linestyle='-', lw=1.0)
    ax.axvline(x=be_lower, color=text_color, linestyle='--', alpha=0.5, label=f'Lower BEP: {be_lower:,.0f}')
    ax.axvline(x=be_upper, color=text_color, linestyle='--', alpha=0.5, label=f'Upper BEP: {be_upper:,.0f}')
    ax.set_title(f"Payoff Graph for Expiry: {expiry_label}", fontsize=14, color=text_color)
    ax.set_xlabel("Stock Price at Expiration", fontsize=12, color=text_color)
    ax.set_ylabel("Profit / Loss (₹)", fontsize=12, color=text_color)
    ax.tick_params(axis='x', colors=text_color)
    ax.tick_params(axis='y', colors=text_color)
    for spine in ['top', 'right']: ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']: ax.spines[spine].set_color(grid_color)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5, color=grid_color)
    ax.legend(facecolor='#1e1e1e', edgecolor=grid_color, labelcolor=text_color)
    filename = f"payoff_{uuid.uuid4().hex}.png"
    filepath = os.path.join(STATIC_FOLDER_PATH, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight', transparent=True)
    plt.close(fig)
    return f'static/{filename}'

def generate_analysis(instrument_name, calculation_type, selected_expiry_str):
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    if not all([instrument_name, calculation_type, selected_expiry_str]): return None, "Please select valid inputs."
    ticker_symbol = TICKERS[instrument_name]
    lot_size = 75 if instrument_name == "NIFTY" else 15
    strike_increment = 50 if instrument_name == "NIFTY" else 100
    df_zones = yf.Ticker(ticker_symbol).history(period="6mo" if calculation_type == "Weekly" and instrument_name == "NIFTY" else "5y", interval="1d")
    if df_zones.empty: return None, "Failed to calculate zones."
    df_zones.index = pd.to_datetime(df_zones.index)
    resample_period = 'W' if calculation_type == "Weekly" else 'ME'
    agg_df = df_zones.resample(resample_period).agg({'Open': 'first', 'High': 'max', 'Low': 'min'}).dropna()
    rng5, rng10 = (agg_df['High'] - agg_df['Low']).rolling(5).mean(), (agg_df['High'] - agg_df['Low']).rolling(10).mean()
    base = agg_df['Open']
    u1, u2 = base + 0.5 * rng5, base + 0.5 * rng10
    l1, l2 = base - 0.5 * rng5, base - 0.5 * rng10
    latest_zones = pd.DataFrame({'u1': u1, 'u2': u2, 'l1': l1, 'l2': l2}).dropna().iloc[-1]
    supply_zone, demand_zone = round(max(latest_zones['u1'], latest_zones['u2']), 2), round(min(latest_zones['l1'], latest_zones['l2']), 2)
    option_chain_data = get_option_chain_data(instrument_name)
    if not option_chain_data: return None, "Error fetching option chain."
    current_price = option_chain_data['records']['underlyingValue']
    expiry_label = datetime.strptime(selected_expiry_str, '%d-%b-%Y').strftime("%d-%b")
    ce_prices, pe_prices = {}, {}
    for item in option_chain_data['records']['data']:
        if item.get("expiryDate") == selected_expiry_str:
            if item.get("CE"): ce_prices[item['strikePrice']] = item["CE"]["lastPrice"]
            if item.get("PE"): pe_prices[item['strikePrice']] = item["PE"]["lastPrice"]
    ce_high = math.ceil(supply_zone / strike_increment) * strike_increment
    strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
    pe_high = math.floor(demand_zone / strike_increment) * strike_increment
    candidate_puts = sorted([s for s in pe_prices if s < pe_high and pe_prices.get(s, 0) > 0], key=lambda s: pe_prices.get(s, 0), reverse=True)
    pe_mid = (candidate_puts[0] if candidate_puts else pe_high - strike_increment)
    pe_low = (candidate_puts[1] if len(candidate_puts) > 1 else pe_mid - strike_increment)
    strikes_pe = [pe_high, pe_mid, pe_low]
    df = pd.DataFrame({"Entry": ["High Reward", "Mid Reward", "Low Reward"], "CE Strike": strikes_ce, "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce], "PE Strike": strikes_pe, "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe]})
    df["Combined Premium"] = df["CE Price"] + df["PE Price"]
    df["Target"] = (df["Combined Premium"] * 0.80 * lot_size).round(2)
    df["Stoploss"] = (df["Combined Premium"] * 0.80 * lot_size).round(2)
    display_df = df[['Entry', 'CE Strike', 'CE Price', 'PE Strike', 'PE Price']].copy()
    display_df['Target/SL (1:1)'] = df['Target']
    title, zone_label = f"FiFTO - {calculation_type} {instrument_name} Selling", calculation_type
    summary_filename = f"summary_{uuid.uuid4().hex}.png"
    summary_filepath = os.path.join(STATIC_FOLDER_PATH, summary_filename)
    fig, ax = plt.subplots(figsize=(10, 5)); fig.patch.set_facecolor('#e0f7fa'); ax.axis('off')
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    info_text = f"{instrument_name}: {current_price}\nExpiry: {expiry_label}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ax.text(0.5, 0.85, info_text, transform=ax.transAxes, ha='center', va='center', fontsize=12, family='monospace')
    table = plt.table(cellText=display_df.values, colLabels=display_df.columns, colColours=['#00acc1'] * len(display_df.columns), cellLoc='center', loc='center')
    table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1.2, 2)
    for (row, col), cell in table.get_celld().items():
        if row == 0: cell.get_text().set_color('white')
    fig.text(0.5, 0.01, "Disclaimer: For educational purposes only.", ha='center', va='bottom', fontsize=7, color='grey', style='italic')
    plt.savefig(summary_filepath, dpi=150, bbox_inches='tight'); plt.close(fig)
    payoff_filepath = generate_payoff_chart(df, lot_size, current_price, instrument_name, zone_label, expiry_label)
    analysis_data = {"instrument": instrument_name, "expiry": selected_expiry_str, "lot_size": lot_size, "df_data": df.to_dict('records'), "summary_file": f'static/{summary_filename}', "payoff_file": payoff_filepath, "display_df_html": display_df.to_html(classes='table table-striped', index=False, justify='center')}
    return analysis_data, f"Charts generated for {instrument_name}."

# --- Trade Action Functions ---
def add_to_analysis(analysis_data):
    if not analysis_data or not analysis_data.get('df_data'): return "Generate an analysis first."
    trades = load_trades()
    new_trades_added = 0
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    day_name = datetime.now().strftime("%A")
    entry_tag = f"{day_name} Selling"
    for entry in analysis_data['df_data']:
        trade_id = f"{analysis_data['instrument']}_{analysis_data['expiry']}_{entry['Entry'].replace(' ', '')}"
        if any(t['id'] == trade_id for t in trades): continue
        trades.append({"id": trade_id, "start_time": start_time, "status": "Running", "entry_tag": entry_tag, "instrument": analysis_data['instrument'], "expiry": analysis_data['expiry'], "reward_type": entry['Entry'], "ce_strike": entry['CE Strike'], "pe_strike": entry['PE Strike'], "initial_premium": entry['Combined Premium'], "target_amount": entry['Target'], "stoploss_amount": entry['Stoploss']})
        new_trades_added += 1
    save_trades(trades)
    return f"Added {new_trades_added} new trade(s) tagged as '{entry_tag}'."

def close_selected_trade(trade_id_to_close):
    all_trades = load_trades()
    trade_to_close = next((t for t in all_trades if t['id'] == trade_id_to_close), None)
    if not trade_to_close: return
    message = f"🔔 *Manual Square-Off Alert* 🔔\n\nPlease square-off the position for Trade ID: `{trade_to_close['id']}`"
    send_telegram_message(message)
    remaining_trades = [t for t in all_trades if t['id'] != trade_id_to_close]
    save_trades(remaining_trades)

def send_daily_chart_to_telegram(analysis_data):
    summary_path = os.path.join(settings.BASE_DIR, analysis_data['summary_file'])
    payoff_path = os.path.join(settings.BASE_DIR, analysis_data['payoff_file'])
    day_name = datetime.now().strftime('%A')
    title = f"📊 **{day_name} Selling Summary**"
    message_lines = [title]
    for entry in analysis_data['df_data']:
        amount = entry['Combined Premium'] * analysis_data['lot_size']
        message_lines.append(f"- {entry['Entry']}: ₹{amount:.2f}")
    return send_telegram_message("\n".join(message_lines), image_paths=[summary_path, payoff_path])

def monitor_trades(is_eod_report=False):
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    trades = load_trades()
    if not trades:
        return

    active_trades = [t for t in trades if t.get('status') == 'Running']
    completed_trades = [t for t in trades if t.get('status') != 'Running']

    # Group trades by instrument for efficient API calls
    instrument_groups = defaultdict(list)
    for trade in active_trades:
        instrument_groups[trade['instrument']].append(trade)

    pl_data_for_image = {'title': f"Live P/L Update", 'tags': defaultdict(list)}
    any_trade_updated = False

    for instrument, trades_in_group in instrument_groups.items():
        chain = get_option_chain_data(instrument)
        if not chain: continue
        lot_size = 75 if instrument == "NIFTY" else 15

        for trade in trades_in_group:
            current_ce, current_pe = 0.0, 0.0
            for item in chain['records']['data']:
                if item.get("expiryDate") == trade['expiry']:
                    if item.get("strikePrice") == trade['ce_strike'] and item.get("CE"):
                        current_ce = item["CE"]["lastPrice"]
                    if item.get("strikePrice") == trade['pe_strike'] and item.get("PE"):
                        current_pe = item["PE"]["lastPrice"]

            if current_ce == 0.0 and current_pe == 0.0: continue

            pnl = (trade['initial_premium'] - (current_ce + current_pe)) * lot_size
            any_trade_updated = True

            tag_key = trade.get('entry_tag', 'General Trades')
            pl_data_for_image['tags'][tag_key].append({'reward_type': trade['reward_type'], 'pnl': pnl})

            # Check for Target or Stoploss
            if pnl >= trade['target_amount']:
                trade['status'] = 'Target'
                msg = f"✅ TARGET HIT: {trade['id']} ({tag_key})\nP/L: ₹{pnl:.2f}"
                send_telegram_message(msg)
            elif pnl <= -trade['stoploss_amount']:
                trade['status'] = 'Stoploss'
                msg = f"❌ STOPLOSS HIT: {trade['id']} ({tag_key})\nP/L: ₹{pnl:.2f}"
                send_telegram_message(msg)

    # Send periodic update image to Telegram
    if any_trade_updated and not is_eod_report:
        image_path = generate_pl_update_image(pl_data_for_image, now)
        send_telegram_message(message="", image_paths=[image_path])
        os.remove(image_path)

    # Save any status changes
    save_trades(active_trades + completed_trades)