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
import traceback

# --- Configuration ---
BOT_TOKEN = "7476365992:AAGjDcQcMB7lkiy92VoDnZwixatakhe02DI"
CHAT_ID = "-1002886512293"
BASE_DIR = os.path.expanduser('~')
TRADES_DB_FILE = os.path.join(BASE_DIR, "active_trades.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "app_settings.json")

# --- Global Scheduler Initialization ---
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))

# --- Settings Management ---
def load_settings():
    """Loads settings from the settings file, providing defaults if it doesn't exist."""
    defaults = {"update_interval": "15 Mins", "schedules": []}
    if not os.path.exists(SETTINGS_FILE): return defaults
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            for key, value in defaults.items(): settings.setdefault(key, value)
            return settings
    except (json.JSONDecodeError, FileNotFoundError): return defaults

def save_settings(settings):
    """Saves the given settings dictionary to the settings file."""
    with open(SETTINGS_FILE, 'w') as f: json.dump(settings, f, indent=4)


# --- Helper & Data Functions ---
def load_trades():
    if not os.path.exists(TRADES_DB_FILE): return []
    try:
        with open(TRADES_DB_FILE, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return []

def save_trades(trades):
    with open(TRADES_DB_FILE, 'w') as f: json.dump(trades, f, indent=4)

def get_option_chain_data(symbol, retries=3, delay=2):
    """Fetches option chain data with a retry mechanism."""
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36', 'Accept': 'application/json, text/javascript, */*; q=0.01', 'Accept-Language': 'en-US,en;q=0.9'}
    api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    for i in range(retries):
        try:
            session.get(f"https://www.nseindia.com/get-quotes/derivatives?symbol={symbol}", headers=headers, timeout=15)
            time.sleep(1)
            response = session.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Attempt {i+1}/{retries} failed for {symbol}: {e}")
            if i < retries - 1:
                time.sleep(delay)
    print(f"All retries failed for {symbol}.")
    return None

def send_telegram_message(message, image_paths=None):
    if BOT_TOKEN == "YOUR_BOT_TOKEN" or CHAT_ID == "YOUR_CHAT_ID": return "Telegram credentials not set."
    try:
        if image_paths:
            if isinstance(image_paths, str): image_paths = [image_paths]
            image_paths = [path for path in image_paths if path and os.path.exists(path)]
            if not image_paths: return send_telegram_message(message) if message else "No valid images to send."
            if len(image_paths) > 1:
                url, files, media = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup", {}, []
                for i, path in enumerate(image_paths):
                    file_name = os.path.basename(path)
                    files[file_name] = open(path, 'rb')
                    photo_media = {'type': 'photo', 'media': f'attach://{file_name}'}
                    if i == 0 and message: photo_media['caption'] = message
                    media.append(photo_media)
                response = requests.post(url, data={'chat_id': CHAT_ID, 'media': json.dumps(media)}, files=files)
                for f in files.values(): f.close()
            elif len(image_paths) == 1:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                with open(image_paths[0], 'rb') as img:
                    response = requests.post(url, data={'chat_id': CHAT_ID, 'caption': message}, files={'photo': img})
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            response = requests.post(url, data={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'})
        response.raise_for_status()
        return "Message sent to Telegram."
    except requests.exceptions.RequestException as e: return f"Failed to send to Telegram: {e}"

# --- Charting Functions ---
def generate_pl_update_image(data_for_image, timestamp):
    num_lines = 1 + sum(len(trades) + 1.5 for _, trades in data_for_image['tags'].items())
    fig_height = max(3, num_lines * 0.4)
    fig, ax = plt.subplots(figsize=(8, fig_height), facecolor='#F4F6F6')
    ax.axis('off')
    fig.text(0.5, 0.95, data_for_image['title'], ha='center', va='top', fontsize=18, fontweight='bold', color='#17202A')
    y_pos, line_height = 0.85, 1.0 / (num_lines + 2)
    for tag, trades in sorted(data_for_image['tags'].items()):
        ax.text(0.1, y_pos, f"{tag}", ha='left', va='top', fontsize=14, fontweight='bold', color='#2980B9')
        y_pos -= line_height * 1.2
        for trade in trades:
            pnl_color = '#27AE60' if trade['pnl'] >= 0 else '#C0392B'
            ax.text(0.15, y_pos, f"• {trade['reward_type']}:", ha='left', va='top', fontsize=13, color='#212F3D')
            ax.text(0.85, y_pos, f"₹{trade['pnl']:,.2f}", ha='right', va='top', fontsize=13, color=pnl_color, family='monospace', weight='bold')
            y_pos -= line_height
        y_pos -= (line_height / 2)
    fig.text(0.98, 0.02, timestamp.strftime("%d-%b-%Y %I:%M:%S %p"), ha='right', va='bottom', fontsize=9, color='#566573')
    filepath = os.path.join(os.path.expanduser('~'), f"pl_update_{uuid.uuid4().hex}.png")
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor(), pad_inches=0.1)
    plt.close(fig)
    return filepath

def generate_payoff_chart(strategies_df, lot_size, current_price, instrument_name, zone_label, expiry_label):
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    price_range = np.linspace(current_price * 0.90, current_price * 1.10, 500)
    max_profit = 0
    for strategy in strategies_df.to_dict('records'):
        if strategy['Entry'] == 'High Reward':
            ce_strike, pe_strike = strategy['CE Strike'], strategy['PE Strike']
            combined_premium = strategy['Combined Premium'] 
            pnl = (combined_premium - np.maximum(price_range - ce_strike, 0) - np.maximum(pe_strike - price_range, 0)) * lot_size
            ax.plot(price_range, pnl, label="Sell Payoff", linewidth=2.5)
            be_upper, be_lower = ce_strike + combined_premium, pe_strike - combined_premium
            max_profit = combined_premium * lot_size
            ax.fill_between(price_range, pnl, 0, where=(pnl >= 0), facecolor='green', alpha=0.3, interpolate=True, label='Profit')
            ax.fill_between(price_range, pnl, 0, where=(pnl <= 0), facecolor='red', alpha=0.3, interpolate=True, label='Loss')
            ax.axvline(x=be_lower, color='grey', linestyle='--', label=f'Lower BEP: {be_lower:,.0f}')
            ax.axvline(x=be_upper, color='grey', linestyle='--', label=f'Upper BEP: {be_upper:,.0f}')
            ax.annotate(f'Max Profit: ₹{max_profit:,.2f}', xy=(current_price, max_profit), xytext=(current_price, max_profit * 0.5), ha='center', va='center', fontsize=11, fontweight='bold', bbox=dict(boxstyle="round,pad=0.5", fc="lightgreen", alpha=0.9))
            break
    ax.set_title(f"Sell Positions Payoff Graph for Expiry: {expiry_label}", fontsize=14)
    fig.suptitle(f"FiFTO {zone_label} Selling - {instrument_name}", fontsize=16, fontweight='bold')
    ax.axhline(y=0, color='black', linestyle='-', lw=1.0)
    ax.set_xlabel("Stock Price at Expiration", fontsize=12)
    ax.set_ylabel("Profit / Loss (₹)", fontsize=12)
    ax.set_ylim(-3 * max_profit if max_profit > 0 else -25000, 1.5 * max_profit if max_profit > 0 else 25000)
    ax.legend()
    fig.text(0.99, 0.01, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', horizontalalignment='right', verticalalignment='bottom', fontsize=8, color='gray')
    filename = f"payoff_{uuid.uuid4().hex}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return filename

def find_hedge_strike(sold_strike, target_premium, options_data, option_type):
    candidates = []
    for strike, price in options_data.items():
        is_valid_direction = (option_type == 'CE' and strike > sold_strike) or (option_type == 'PE' and strike < sold_strike)
        if is_valid_direction and strike % 100 == 0:
            candidates.append({'strike': strike, 'price': price, 'diff': abs(price - target_premium)})
    return min(candidates, key=lambda x: x['diff'])['strike'] if candidates else None

def generate_hedge_image(df, instrument_name, expiry_label):
    hedge_df = df[['Entry', 'CE Hedge Strike', 'CE Hedge Price', 'PE Hedge Strike', 'PE Hedge Price']].copy()
    hedge_df.rename(columns={'Entry': 'Strategy', 'CE Hedge Strike': 'Buy Call Strike', 'CE Hedge Price': 'Price (CE)', 'PE Hedge Strike': 'Buy Put Strike', 'PE Hedge Price': 'Price (PE)'}, inplace=True)
    fig, ax = plt.subplots(figsize=(10, 4), facecolor='#F0F3F4')
    ax.axis('off')
    fig.suptitle(f"{instrument_name} - Hedge Positions to BUY", fontsize=16, fontweight='bold', y=0.95)
    ax.text(0.5, 0.82, f"For Expiry: {expiry_label}", transform=ax.transAxes, ha='center', va='center', fontsize=12, family='monospace')
    table = plt.table(cellText=hedge_df.values, colLabels=hedge_df.columns, colColours=['#27AE60'] * len(hedge_df.columns), cellLoc='center', loc='center')
    table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1.2, 2.0)
    for (row, col), cell in table.get_celld().items():
        if row == 0: cell.get_text().set_color('white')
    fig.text(0.5, 0.01, "These positions are intended to hedge the primary sell trades.", ha='center', va='bottom', fontsize=8, color='grey', style='italic')
    filename = f"hedge_{uuid.uuid4().hex}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return filename

def generate_analysis(instrument_name, calculation_type, selected_expiry_str, hedge_premium_percentage):
    if not selected_expiry_str or "Loading..." in selected_expiry_str or "Error" in selected_expiry_str:
        return None, None, None, "Expiry Date has not loaded. Please wait or re-select the Index to try again.", None, None, None, None
    try:
        TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        print("Initializing...")
        lot_size, strike_increment = 25 if instrument_name == "NIFTY" else 15, 50 if instrument_name == "NIFTY" else 100
        print(f"Calculating {calculation_type} zones...")
        
        # Try multiple approaches for data fetching
        df_zones = None
        ticker_symbol = TICKERS[instrument_name]
        
        # Try different time periods if data is not available
        periods_to_try = ["6mo", "1y", "2y", "max"]
        for period in periods_to_try:
            try:
                print(f"Trying to fetch data with period: {period}")
                df_zones = yf.Ticker(ticker_symbol).history(period=period, interval="1d")
                if not df_zones.empty:
                    print(f"Successfully fetched data with period: {period}")
                    break
                else:
                    print(f"No data returned for period: {period}")
            except Exception as e:
                print(f"Error with period {period}: {e}")
                continue
        
        # If yfinance fails, use alternative zone calculation
        if df_zones is None or df_zones.empty:
            print("yfinance data unavailable, using alternative zone calculation...")
            # Get current price from option chain instead
            option_chain_data = get_option_chain_data(instrument_name)
            if not option_chain_data: 
                return None, None, None, f"Error: Unable to fetch data for {instrument_name}. Please try again later.", None, None, None, None
            
            current_price = option_chain_data['records']['underlyingValue']
            print(f"Current price from option chain: {current_price}")
            
            # Use simple percentage-based zones as fallback
            supply_zone = current_price * 1.02  # 2% above current price
            demand_zone = current_price * 0.98  # 2% below current price
            print(f"Using fallback zones - Supply: {supply_zone}, Demand: {demand_zone}")
        else:
            # Original zone calculation with fetched data
            df_zones.index = pd.to_datetime(df_zones.index)
            period_rule = 'W' if calculation_type == "Weekly" else 'ME'
            agg_df = df_zones.resample(period_rule).agg({'Open': 'first', 'High': 'max', 'Low': 'min'}).dropna()
            
            if agg_df.empty:
                print("Aggregated data is empty, using fallback zones...")
                option_chain_data = get_option_chain_data(instrument_name)
                if not option_chain_data: 
                    return None, None, None, f"Error: Unable to fetch data for {instrument_name}.", None, None, None, None
                current_price = option_chain_data['records']['underlyingValue']
                supply_zone = current_price * 1.02
                demand_zone = current_price * 0.98
            else:
                base = agg_df['Open']
                rng5 = (agg_df['High'] - agg_df['Low']).rolling(min(5, len(agg_df))).mean()
                rng10 = (agg_df['High'] - agg_df['Low']).rolling(min(10, len(agg_df))).mean()
                latest_zones = pd.DataFrame({'u1': base + 0.5*rng5, 'u2': base + 0.5*rng10, 'l1': base - 0.5*rng5, 'l2': base - 0.5*rng10}).dropna()
                
                if latest_zones.empty:
                    print("Zone calculation failed, using fallback...")
                    option_chain_data = get_option_chain_data(instrument_name)
                    if not option_chain_data: 
                        return None, None, None, f"Error: Unable to fetch data for {instrument_name}.", None, None, None, None
                    current_price = option_chain_data['records']['underlyingValue']
                    supply_zone = current_price * 1.02
                    demand_zone = current_price * 0.98
                else:
                    latest_zone_data = latest_zones.iloc[-1]
                    supply_zone = round(max(latest_zone_data['u1'], latest_zone_data['u2']), 2)
                    demand_zone = round(min(latest_zone_data['l1'], latest_zone_data['l2']), 2)
        
        print("Fetching option chain...")
        option_chain_data = get_option_chain_data(instrument_name)
        if not option_chain_data: return None, None, None, f"Error fetching option chain.", None, None, None, None
        current_price, expiry_label = option_chain_data['records']['underlyingValue'], datetime.strptime(selected_expiry_str, '%d-%b-%Y').strftime("%d-%b")
        print("Parsing data...")
        ce_prices, pe_prices = {}, {}
        for item in option_chain_data['records']['data']:
            if item.get("expiryDate") == selected_expiry_str:
                if item.get("CE"): ce_prices[item['strikePrice']] = item["CE"]["lastPrice"]
                if item.get("PE"): pe_prices[item['strikePrice']] = item["PE"]["lastPrice"]
        ce_high = math.ceil(supply_zone / strike_increment) * strike_increment
        strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
        pe_high = math.floor(demand_zone / strike_increment) * strike_increment
        candidate_puts = sorted([s for s in pe_prices if s < pe_high and pe_prices.get(s, 0) > 0], key=lambda s: pe_prices.get(s, 0), reverse=True)
        pe_mid, pe_low = (candidate_puts[0] if candidate_puts else pe_high - strike_increment), (candidate_puts[1] if len(candidate_puts) > 1 else (candidate_puts[0] if candidate_puts else pe_high - strike_increment) - strike_increment)
        strikes_pe = [pe_high, pe_mid, pe_low]
        print("Finding suitable hedges...")
        temp_df = pd.DataFrame({"CE Strike": strikes_ce, "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce], "PE Strike": strikes_pe, "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe]})
        hedge_premium_decimal, strikes_ce_hedge, strikes_pe_hedge = hedge_premium_percentage / 100.0, [], []
        for _, row in temp_df.iterrows():
            strikes_ce_hedge.append(find_hedge_strike(row['CE Strike'], row['CE Price'] * hedge_premium_decimal, ce_prices, 'CE') or row['CE Strike'] + 1000)
            strikes_pe_hedge.append(find_hedge_strike(row['PE Strike'], row['PE Price'] * hedge_premium_decimal, pe_prices, 'PE') or row['PE Strike'] - 1000)
        print("Creating charts...")
        df = pd.DataFrame({"Entry": ["High Reward", "Mid Reward", "Low Reward"], "CE Strike": strikes_ce, "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce], "PE Strike": strikes_pe, "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe], "CE Hedge Strike": strikes_ce_hedge, "CE Hedge Price": [ce_prices.get(s, 0.0) for s in strikes_ce_hedge], "PE Hedge Strike": strikes_pe_hedge, "PE Hedge Price": [pe_prices.get(s, 0.0) for s in strikes_pe_hedge]})
        df["Combined Premium"], df["Net Premium"] = df["CE Price"] + df["PE Price"], (df["CE Price"] + df["PE Price"]) - (df["CE Hedge Price"] + df["PE Hedge Price"])
        df["Target"], df["Stoploss"] = (df["Net Premium"] * 0.80 * lot_size).round(2), (df["Net Premium"] * 0.80 * lot_size).round(2)
        display_df = df[['Entry', 'CE Strike', 'CE Price', 'PE Strike', 'PE Price', 'Combined Premium']].copy()
        display_df['Target/SL'] = (display_df['Combined Premium'] * 0.80 * lot_size).round(2)
        display_df.rename(columns={'Combined Premium': 'Sell Premium'}, inplace=True)
        title, summary_filename = f"FiFTO - {calculation_type} {instrument_name} SELL Positions", f"{instrument_name}_{calculation_type}_Summary.png"
        fig, ax = plt.subplots(figsize=(10, 5)); fig.patch.set_facecolor('#e0f7fa'); ax.axis('off')
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        ax.text(0.5, 0.85, f"{instrument_name}: {current_price}\nExpiry: {expiry_label}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", transform=ax.transAxes, ha='center', va='center', fontsize=12, family='monospace')
        table = plt.table(cellText=display_df.values, colLabels=display_df.columns, colColours=['#C0392B'] * len(display_df.columns), cellLoc='center', loc='center')
        table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1.2, 2.0)
        for (row, col), cell in table.get_celld().items():
            if row == 0: cell.get_text().set_color('white')
        fig.text(0.5, 0.01, "Disclaimer: For educational purposes only. Not SEBI registered.", ha='center', va='bottom', fontsize=7, color='grey', style='italic')
        plt.savefig(summary_filename, dpi=300, bbox_inches='tight'); plt.close(fig)
        hedge_filename = generate_hedge_image(df, instrument_name, expiry_label)
        payoff_filename = generate_payoff_chart(df, lot_size, current_price, instrument_name, calculation_type, expiry_label)
        analysis_data = {"instrument": instrument_name, "expiry": selected_expiry_str, "lot_size": lot_size, "df_data": df.to_dict('records')}
        print(f"Analysis completed successfully for {instrument_name}")
        return summary_filename, hedge_filename, payoff_filename, f"Charts generated for {instrument_name}. Supply Zone: {supply_zone:.2f}, Demand Zone: {demand_zone:.2f}", analysis_data, summary_filename, hedge_filename, payoff_filename
    except Exception as e:
        print(f"Error in generate_analysis: {e}")
        traceback.print_exc()
        return None, None, None, f"An error occurred: {e}", None, None, None, None

# --- Trade Management & Monitoring ---
def add_trades_to_db(analysis_data):
    if not analysis_data or not analysis_data['df_data']: return "No analysis data to add."
    trades, new_trades_added, entry_tag = load_trades(), 0, f"{datetime.now().strftime('%A')} Selling"
    for entry in analysis_data['df_data']:
        trade_id = f"{analysis_data['instrument']}_{analysis_data['expiry']}_{entry['Entry'].replace(' ', '')}_{entry_tag.replace(' ', '')}"
        if any(t['id'] == trade_id for t in trades): continue
        trades.append({"id": trade_id, "start_time": datetime.now().strftime("%Y-%m-%d %H:%M"), "instrument": analysis_data['instrument'], "expiry": analysis_data['expiry'], "reward_type": entry['Entry'], "ce_strike": entry['CE Strike'], "pe_strike": entry['PE Strike'], "ce_hedge_strike": entry['CE Hedge Strike'], "pe_hedge_strike": entry['PE Hedge Strike'], "initial_net_premium": entry['Net Premium'], "target_amount": entry['Target'], "stoploss_amount": entry['Stoploss'], "status": "Running", "entry_tag": entry_tag})
        new_trades_added += 1
    if new_trades_added > 0:
        save_trades(trades)
        return f"Added {new_trades_added} new trade(s) tagged as '{entry_tag}'."
    return "No new trades were added. They may already exist in the analysis."

def add_to_analysis(analysis_data):
    message = add_trades_to_db(analysis_data)
    return message, gr.DataFrame(value=load_trades_for_display())

def load_trades_for_display():
    trades = load_trades()
    if not trades: return pd.DataFrame(columns=["ID", "Tag", "Start Time", "Status", "Initial Net Credit (₹)", "Target Profit (₹)", "Stoploss (₹)"])
    df = pd.DataFrame(trades)
    df['lot_size'] = df['instrument'].apply(lambda x: 25 if x == 'NIFTY' else 15)
    if 'initial_net_premium' in df.columns:
        if 'initial_premium' in df.columns: df.loc[:, 'initial_net_premium'] = df['initial_net_premium'].fillna(df['initial_premium'])
        df.loc[:, 'initial_amount'] = (df['initial_net_premium'] * df['lot_size']).round()
    elif 'initial_premium' in df.columns: df.loc[:, 'initial_amount'] = (df['initial_premium'] * df['lot_size']).round()
    else: df['initial_amount'] = 0
    df['start_time'] = df.get('start_time', 'N/A')
    df['entry_tag'] = df.get('entry_tag', 'N/A')
    display_df = df[['id', 'entry_tag', 'start_time', 'status', 'initial_amount', 'target_amount', 'stoploss_amount']].copy()
    display_df.rename(columns={'id': 'ID', 'entry_tag': 'Tag', 'start_time': 'Start Time', 'status': 'Status', 'initial_amount': 'Initial Net Credit (₹)', 'target_amount': 'Target Profit (₹)', 'stoploss_amount': 'Stoploss (₹)'}, inplace=True)
    return display_df

def close_selected_trade(trades_df, selected_index):
    if selected_index is None or not isinstance(selected_index, int) or trades_df.empty:
        return trades_df, "Please select a trade to close first.", None
    all_trades = load_trades()
    trade_id_to_close = trades_df.iloc[selected_index]['ID']
    selected_trade = next((t for t in all_trades if t['id'] == trade_id_to_close), None)
    if not selected_trade: return load_trades_for_display(), f"Error: Trade with ID {trade_id_to_close} not found.", None
    tag_to_close = selected_trade.get('entry_tag')
    if not tag_to_close: return load_trades_for_display(), "Error: Selected trade does not have a tag for group closing.", None
    trades_in_group = [t for t in all_trades if t.get('entry_tag') == tag_to_close]
    instrument = trades_in_group[0]['instrument']
    chain = get_option_chain_data(instrument)
    message = f"🔔 *Manual Group Square-Off Alert: {tag_to_close}* 🔔\n\nPlease square-off all positions for this group:\n\n"
    for trade in trades_in_group:
        current_ce, current_pe, current_ce_hedge, current_pe_hedge = 0.0, 0.0, 0.0, 0.0
        if chain:
            for item in chain['records']['data']:
                if item['expiryDate'] == trade['expiry']:
                    if item['strikePrice'] == trade['ce_strike'] and item.get('CE'): current_ce = item['CE']['lastPrice']
                    if item['strikePrice'] == trade['pe_strike'] and item.get('PE'): current_pe = item['PE']['lastPrice']
                    if item['strikePrice'] == trade.get('ce_hedge_strike') and item.get('CE'): current_ce_hedge = item['CE']['lastPrice']
                    if item['strikePrice'] == trade.get('pe_hedge_strike') and item.get('PE'): current_pe_hedge = item['PE']['lastPrice']
        message += (f"*Trade: {trade['reward_type']}*\n"
                    f"  - SELL CE {trade['ce_strike']}: `₹{current_ce:.2f}`\n  - SELL PE {trade['pe_strike']}: `₹{current_pe:.2f}`\n"
                    f"  - BUY CE {trade['ce_hedge_strike']}: `₹{current_ce_hedge:.2f}`\n  - BUY PE {trade['pe_hedge_strike']}: `₹{current_pe_hedge:.2f}`\n\n")
    send_telegram_message(message)
    remaining_trades = [t for t in all_trades if t.get('entry_tag') != tag_to_close]
    save_trades(remaining_trades)
    return load_trades_for_display(), f"Square-off alert for group '{tag_to_close}' sent.", None

def clear_old_trades():
    all_trades = load_trades()
    if not all_trades: return load_trades_for_display(), "No trades to clear."
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    active_trades = [t for t in all_trades if t.get('status') == 'Running' and datetime.strptime(t['expiry'], '%d-%b-%Y').date() >= now.date()]
    removed_count = len(all_trades) - len(active_trades)
    if removed_count == 0: message = "No old trades found to clear."
    else: save_trades(active_trades); message = f"Successfully cleared {removed_count} old/completed trade(s)."
    return load_trades_for_display(), message

def clear_all_trades():
    all_trades = load_trades()
    if not all_trades: return load_trades_for_display(), "Trade list is already empty."
    removed_count = len(all_trades)
    save_trades([])
    return load_trades_for_display(), f"Successfully cleared all {removed_count} trade(s)."

def check_for_ts_hits():
    print(f"[{datetime.now(pytz.timezone('Asia/Kolkata'))}] Running high-frequency T/S check...")
    trades_to_update = load_trades()
    active_trades = [t for t in trades_to_update if t.get('status') == 'Running']
    if not active_trades: return
    trades_by_instrument = defaultdict(list)
    for trade in active_trades: trades_by_instrument[trade['instrument']].append(trade)
    something_was_updated = False
    for instrument, trades in trades_by_instrument.items():
        chain, lot_size = get_option_chain_data(instrument), 25 if instrument == "NIFTY" else 15
        if not chain: continue
        for trade in trades:
            if trade['status'] != 'Running': continue
            current_ce, current_pe, current_ce_hedge, current_pe_hedge = 0.0, 0.0, 0.0, 0.0
            for item in chain['records']['data']:
                if item['expiryDate'] == trade['expiry']:
                    if item['strikePrice'] == trade['ce_strike'] and item.get('CE'): current_ce = item['CE']['lastPrice']
                    if item['strikePrice'] == trade['pe_strike'] and item.get('PE'): current_pe = item['PE']['lastPrice']
                    if item['strikePrice'] == trade['ce_hedge_strike'] and item.get('CE'): current_ce_hedge = item['CE']['lastPrice']
                    if item['strikePrice'] == trade['pe_hedge_strike'] and item.get('PE'): current_pe_hedge = item['PE']['lastPrice']
            pnl = (trade.get('initial_net_premium', 0) - ((current_ce + current_pe) - (current_ce_hedge + current_pe_hedge))) * lot_size
            if pnl >= trade['target_amount']:
                trade['status'], msg = 'Target', f"✅ TARGET HIT: {trade['id']} ({trade.get('entry_tag')})\nP/L: ₹{pnl:.2f}"
                print(msg); send_telegram_message(msg); something_was_updated = True
            elif pnl <= -trade['stoploss_amount']:
                trade['status'], msg = 'Stoploss', f"❌ STOPLOSS HIT: {trade['id']} ({trade.get('entry_tag')})\nP/L: ₹{pnl:.2f}"
                print(msg); send_telegram_message(msg); something_was_updated = True
    if something_was_updated: save_trades(trades_to_update)

def send_pl_summary(is_eod_report=False):
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    print(f"[{now}] Running P/L summary generation...")
    trades = load_trades()
    active_trades = [t for t in trades if t.get('status') == 'Running' and datetime.strptime(t['expiry'], '%d-%b-%Y').date() >= now.date()]
    if not active_trades: return
    trade_groups = defaultdict(lambda: defaultdict(list))
    for trade in active_trades: trade_groups[f"{trade['instrument']}_{trade['expiry']}"][trade.get('entry_tag', 'General')].append(trade)
    eod_summary_data = []
    for group_key, tagged_trades in trade_groups.items():
        instrument, expiry = group_key.split('_')
        chain, lot_size = get_option_chain_data(instrument), 25 if instrument == "NIFTY" else 15
        if not chain: continue
        pl_data_for_image, any_trade_updated = {'title': f"{instrument} {expiry} P/L Update", 'tags': defaultdict(list)}, False
        for tag, trades_in_group in sorted(tagged_trades.items()):
            for trade in trades_in_group:
                current_ce, current_pe, current_ce_hedge, current_pe_hedge = 0.0, 0.0, 0.0, 0.0
                for item in chain['records']['data']:
                    if item['expiryDate'] == trade['expiry']:
                        if item['strikePrice'] == trade['ce_strike'] and item.get('CE'): current_ce = item['CE']['lastPrice']
                        if item['strikePrice'] == trade['pe_strike'] and item.get('PE'): current_pe = item['PE']['lastPrice']
                        if item['strikePrice'] == trade['ce_hedge_strike'] and item.get('CE'): current_ce_hedge = item['CE']['lastPrice']
                        if item['strikePrice'] == trade['pe_hedge_strike'] and item.get('PE'): current_pe_hedge = item['PE']['lastPrice']
                if current_ce == 0.0 and current_pe == 0.0: continue
                pnl = (trade.get('initial_net_premium', 0) - ((current_ce + current_pe) - (current_ce_hedge + current_pe_hedge))) * lot_size
                any_trade_updated = True
                if is_eod_report: eod_summary_data.append(f"-> {trade['id']}: P/L: ₹{pnl:.2f}")
                else: pl_data_for_image['tags'][tag].append({'reward_type': trade['reward_type'], 'pnl': pnl})
        if not is_eod_report and any_trade_updated:
            image_path = generate_pl_update_image(pl_data_for_image, now); send_telegram_message(message="", image_paths=[image_path]); os.remove(image_path)
    if is_eod_report and eod_summary_data: send_telegram_message(f"--- EOD Summary ({now.strftime('%d-%b-%Y %I:%M %p')}) ---\n" + "\n".join(eod_summary_data))

# --- Auto-Generation and UI Lifecycle ---
def run_scheduled_analysis(schedule_id, index, calc_type):
    print(f"--- Running scheduled job '{schedule_id}' at {datetime.now(pytz.timezone('Asia/Kolkata'))} ---")
    hedge_perc = 10.0
    data = get_option_chain_data(index)
    if not (data and 'records' in data and 'expiryDates' in data['records']): print(f"Scheduled run '{schedule_id}' failed: Could not fetch option chain."); return
    future_expiries = sorted([d for d in data['records']['expiryDates'] if datetime.strptime(d, "%d-%b-%Y").date() >= datetime.now().date()], key=lambda x: datetime.strptime(x, "%d-%b-%Y"))
    if not future_expiries: print(f"Scheduled run '{schedule_id}' failed: No future expiry dates found."); return
    summary_path, hedge_path, payoff_path, _, analysis_data, _, _, _ = generate_analysis(index, calc_type, future_expiries[0], hedge_perc)
    add_msg = add_trades_to_db(analysis_data)
    print(add_msg)
    send_daily_chart_to_telegram(summary_path, hedge_path, payoff_path, analysis_data)
    send_telegram_message(f"🤖 *Auto-Generation Successful ({index})* 🤖\n\n{add_msg}")

def sync_scheduler_with_settings():
    print("--- Syncing scheduler with settings... ---")
    settings = load_settings()
    for job in scheduler.get_jobs():
        if job.id.startswith('auto_generate_job_'): scheduler.remove_job(job.id)
    day_map = {"Monday": "mon", "Tuesday": "tue", "Wednesday": "wed", "Thursday": "thu", "Friday": "fri"}
    for schedule_item in settings.get('schedules', []):
        if schedule_item.get('enabled', False) and schedule_item.get('days') and schedule_item.get('time'):
            try:
                hour, minute = map(int, schedule_item['time'].split(':'))
                day_str = ",".join([day_map[d] for d in schedule_item['days']])
                job_id = f"auto_generate_job_{schedule_item['id']}"
                scheduler.add_job(run_scheduled_analysis, 'cron', day_of_week=day_str, hour=hour, minute=minute, id=job_id, timezone=pytz.timezone('Asia/Kolkata'), misfire_grace_time=600, args=[schedule_item['id'], schedule_item['index'], schedule_item['calc_type']])
                print(f"Scheduled job '{job_id}' for {schedule_item['index']} on {day_str} at {schedule_item['time']}")
            except Exception as e:
                print(f"Could not load schedule '{schedule_item.get('id')}': {e}")

def load_schedules_for_display():
    settings = load_settings()
    df_data = [[s.get('id'), s.get('enabled', False), ", ".join(s.get('days', [])), s.get('time'), s.get('index'), s.get('calc_type')] for s in settings.get('schedules', [])]
    return pd.DataFrame(df_data, columns=['ID', 'Enabled', 'Days', 'Time', 'Index', 'Calculation'])

def add_new_schedule(days, time_str, index, calc_type):
    if not all([days, time_str, index, calc_type]):
        return load_schedules_for_display(), "All fields are required to add a schedule."
    settings = load_settings()
    new_schedule = {"id": uuid.uuid4().hex[:8], "enabled": True, "days": days, "time": time_str, "index": index, "calc_type": calc_type}
    settings['schedules'].append(new_schedule)
    save_settings(settings)
    sync_scheduler_with_settings()
    return load_schedules_for_display(), f"Successfully added new schedule for {index}."

def delete_schedule_by_id(schedule_id_to_delete):
    """Deletes a schedule by its unique ID."""
    if not schedule_id_to_delete:
        return load_schedules_for_display(), "Please select a schedule from the table to delete."
    settings = load_settings()
    initial_len = len(settings['schedules'])
    settings['schedules'] = [s for s in settings['schedules'] if s.get('id') != schedule_id_to_delete]
    if len(settings['schedules']) == initial_len:
        return load_schedules_for_display(), f"Error: Could not find schedule ID {schedule_id_to_delete}."
    save_settings(settings)
    sync_scheduler_with_settings()
    return load_schedules_for_display(), f"Successfully deleted schedule {schedule_id_to_delete}."

def update_expiry_dates(index_name):
    data = get_option_chain_data(index_name)
    if data and 'records' in data and 'expiryDates' in data['records']:
        future_expiries = sorted([d for d in data['records']['expiryDates'] if datetime.strptime(d, "%d-%b-%Y").date() >= datetime.now().date()], key=lambda x: datetime.strptime(x, "%d-%b-%Y"))
        return gr.Dropdown(choices=future_expiries, value=future_expiries[0] if future_expiries else None, interactive=True)
    return gr.Dropdown(choices=["Error: Could not fetch dates."], value="Error: Could not fetch dates.", interactive=False)

def update_monitoring_interval(interval_str):
    try:
        job_id = 'pl_summary'
        if interval_str == "Disable": scheduler.pause_job(job_id); msg = "P/L summary disabled."
        else:
            value, unit = map(str.strip, interval_str.split())
            if unit == 'Mins': scheduler.reschedule_job(job_id, trigger='interval', minutes=int(value))
            elif unit == 'Hour': scheduler.reschedule_job(job_id, trigger='interval', hours=int(value))
            scheduler.resume_job(job_id); msg = f"P/L summary interval set to {interval_str}."
        current_settings = load_settings(); current_settings['update_interval'] = interval_str; save_settings(current_settings)
        print(msg); return msg
    except Exception as e: return f"Failed to update schedule: {e}"

def send_daily_chart_to_telegram(summary_path, hedge_path, payoff_path, analysis_data):
    if not analysis_data: return "Generate charts first."
    day_name, title = datetime.now().strftime('%A'), "📊 **Chart Summary**"
    if day_name in ["Friday", "Monday"]: title = f"📊 **{day_name} Selling Summary**"
    message_lines = [title] + [f"- {entry['Entry']} Reward (Net Credit): ₹{entry['Net Premium'] * analysis_data['lot_size']:.2f}" for entry in analysis_data['df_data']]
    send_telegram_message("\n".join(message_lines), image_paths=[summary_path, hedge_path, payoff_path])
    return "Message with all 3 charts sent to Telegram."

def close_trade_group_by_tag(tag_to_close, current_df):
    """UI wrapper to find the index for a given tag and call the main close function."""
    if not tag_to_close:
        return current_df, "Please select a group from the dropdown first."
    try:
        matching_indices = current_df.index[current_df['Tag'] == tag_to_close].tolist()
        if not matching_indices:
            return current_df, f"Could not find group '{tag_to_close}' in the current list."
        selected_index = matching_indices[0]
        df_result, msg_result, _ = close_selected_trade(current_df, selected_index)
        return df_result, msg_result
    except Exception as e:
        traceback.print_exc()
        return current_df, f"An error occurred while closing the group: {e}"

def build_ui():
    # Custom CSS for professional styling
    custom_css = """
    <style>
    /* Professional FiFTO INDEX Option Selling Platform - Light Mode */
    :root {
        --primary-color: #2563eb;
        --primary-dark: #1d4ed8;
        --primary-light: #60a5fa;
        --secondary-color: #64748b;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --danger-color: #ef4444;
        --info-color: #06b6d4;
        --background-color: #fafbfc;
        --card-background: #ffffff;
        --header-gradient: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        --card-shadow: 0 1px 3px rgba(0,0,0,0.04);
        --card-shadow-hover: 0 4px 12px rgba(0,0,0,0.08);
        --border-radius: 12px;
        --border-radius-small: 6px;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --border-color: #e2e8f0;
        --accent-gradient: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);
    }

    .gradio-container {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
        min-height: 100vh;
        font-family: 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', system-ui, sans-serif !important;
        color: var(--text-primary) !important;
        padding: 24px !important;
    }

    .main-header {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white !important;
        padding: 48px 40px;
        border-radius: var(--border-radius);
        text-align: center;
        margin-bottom: 32px;
        box-shadow: var(--card-shadow);
        position: relative;
        overflow: hidden;
        border: none;
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="0.5"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
        opacity: 0.2;
    }

    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 16px;
        color: white !important;
        position: relative;
        z-index: 1;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .subtitle {
        font-size: 1.25rem;
        font-weight: 500;
        margin-top: 8px;
        color: rgba(255, 255, 255, 0.9) !important;
        position: relative;
        z-index: 1;
    }

    .professional-card {
        background: var(--card-background) !important;
        border-radius: var(--border-radius) !important;
        box-shadow: var(--card-shadow) !important;
        border: 1px solid var(--border-color) !important;
        margin: 20px 0 !important;
        padding: 32px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
    }

    .professional-card:hover {
        box-shadow: var(--card-shadow-hover) !important;
        transform: translateY(-1px) !important;
        border-color: var(--primary-light) !important;
    }

    .professional-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 2px;
        background: var(--accent-gradient);
    }

    .tab-container {
        background: var(--card-background);
        border-radius: var(--border-radius);
        padding: 8px;
        margin-bottom: 24px;
        box-shadow: var(--card-shadow);
        border: 1px solid var(--border-color);
    }

    .tab-nav button {
        background: var(--background-color) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        padding: 12px 20px !important;
        margin: 0 4px !important;
        border-radius: var(--border-radius-small) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        font-size: 14px !important;
        position: relative !important;
        overflow: hidden !important;
    }

    .tab-nav button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: var(--accent-gradient);
        opacity: 0.05;
        transition: left 0.3s ease;
    }

    .tab-nav button:hover {
        background: var(--card-background) !important;
        color: var(--primary-color) !important;
        border-color: var(--primary-light) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15) !important;
    }

    .tab-nav button:hover::before {
        left: 100%;
    }

    .tab-nav button.selected {
        background: var(--primary-color) !important;
        color: white !important;
        border-color: var(--primary-color) !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25) !important;
        font-weight: 600 !important;
    }

    .info-panel {
        background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
        border: 1px solid var(--border-color);
        border-left: 3px solid var(--primary-color);
        padding: 20px;
        border-radius: var(--border-radius-small);
        margin: 20px 0;
        color: var(--text-primary);
        font-size: 14px;
        box-shadow: var(--card-shadow);
        position: relative;
        overflow: hidden;
    }

    .info-panel::before {
        content: '';
        position: absolute;
        top: 10px;
        right: 15px;
        width: 32px;
        height: 32px;
        background: var(--primary-color);
        opacity: 0.08;
        border-radius: 50%;
    }

    .professional-input label {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        margin-bottom: 8px !important;
        font-size: 14px !important;
        display: block !important;
    }

    .professional-input input, 
    .professional-input select, 
    .professional-input textarea {
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius-small) !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        background: var(--card-background) !important;
        color: var(--text-primary) !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }

    .professional-input input:focus, 
    .professional-input select:focus, 
    .professional-input textarea:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
        outline: none !important;
        background: var(--card-background) !important;
    }

    .professional-input input:hover, 
    .professional-input select:hover, 
    .professional-input textarea:hover {
        border-color: var(--primary-light) !important;
    }

    .action-button {
        font-weight: 600 !important;
        padding: 12px 24px !important;
        border-radius: var(--border-radius-small) !important;
        border: none !important;
        cursor: pointer !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        font-size: 14px !important;
        position: relative !important;
        overflow: hidden !important;
        text-transform: none !important;
        letter-spacing: 0.025em !important;
        min-width: 100px !important;
    }

    .action-button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        transform: translate(-50%, -50%);
        transition: width 0.4s, height 0.4s;
    }

    .action-button:active::before {
        width: 200px;
        height: 200px;
    }

    .primary-button {
        background: var(--primary-color) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2) !important;
    }

    .primary-button:hover {
        background: var(--primary-dark) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
    }

    .secondary-button {
        background: var(--secondary-color) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(100, 116, 139, 0.2) !important;
    }

    .secondary-button:hover {
        background: #475569 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(100, 116, 139, 0.3) !important;
    }

    .danger-button {
        background: var(--danger-color) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2) !important;
    }

    .danger-button:hover {
        background: #dc2626 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3) !important;
    }

    .success-button {
        background: var(--success-color) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2) !important;
    }

    .success-button:hover {
        background: #059669 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
    }

    .status-display {
        background: var(--background-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius-small) !important;
        padding: 16px !important;
        font-family: 'SF Mono', 'Monaco', 'Cascadia Code', 'Roboto Mono', 'Menlo', monospace !important;
        color: var(--text-primary) !important;
        font-size: 13px !important;
        line-height: 1.5 !important;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.05) !important;
    }

    .professional-table {
        border-radius: var(--border-radius) !important;
        overflow: hidden !important;
        box-shadow: var(--card-shadow) !important;
        background: var(--card-background) !important;
        border: 1px solid var(--border-color) !important;
    }

    .professional-table table {
        width: 100% !important;
        border-collapse: collapse !important;
    }

    .professional-table th {
        background: var(--background-color) !important;
        color: var(--text-primary) !important;
        padding: 16px 20px !important;
        font-weight: 600 !important;
        text-align: left !important;
        font-size: 13px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        border-bottom: 2px solid var(--border-color) !important;
        border-right: 1px solid var(--border-color) !important;
    }

    .professional-table th:last-child {
        border-right: none !important;
    }

    .professional-table td {
        padding: 14px 20px !important;
        border-bottom: 1px solid var(--border-color) !important;
        font-size: 14px !important;
        color: var(--text-primary) !important;
        border-right: 1px solid var(--border-color) !important;
    }

    .professional-table td:last-child {
        border-right: none !important;
    }

    .professional-table tr:last-child td {
        border-bottom: none !important;
    }

    .professional-table tr:hover {
        background: var(--background-color) !important;
        transition: background 0.2s ease !important;
    }

    .professional-table tr:nth-child(even) {
        background: #f8f9fa !important;
    }

    .professional-table tr:hover {
        background: #e3f2fd !important;
        transition: background 0.3s ease !important;
    }

    .professional-accordion {
        border: 2px solid #e1e5e9 !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        margin: 10px 0 !important;
    }

    .professional-accordion summary {
        background: #f8f9fa !important;
        padding: 14px !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        cursor: pointer !important;
        transition: background 0.3s ease !important;
    }

    .professional-accordion summary:hover {
        background: #e9ecef !important;
    }

    /* Animation keyframes */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }

    .action-button:active {
        animation: pulse 0.3s ease-in-out !important;
    }

    /* Responsive design */
    @media (max-width: 768px) {
        .main-title {
            font-size: 2.2em !important;
        }
        .main-header {
            padding: 20px !important;
        }
        .action-button {
            padding: 12px 20px !important;
            font-size: 12px !important;
        }
        .professional-card {
            padding: 20px !important;
        }
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-dark);
    }

    /* Additional text visibility fixes for Light Mode */
    .gradio-container .gr-form label,
    .gradio-container .gr-textbox label,
    .gradio-container .gr-dropdown label,
    .gradio-container .gr-slider label,
    .gradio-container .gr-radio label,
    .gradio-container .gr-checkbox label {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    .gradio-container .gr-form input,
    .gradio-container .gr-textbox input,
    .gradio-container .gr-dropdown select,
    .gradio-container .gr-slider input {
        color: var(--text-primary) !important;
        background: var(--card-background) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius-small) !important;
    }

    .gradio-container .gr-button {
        color: white !important;
        font-weight: 600 !important;
        border-radius: var(--border-radius-small) !important;
    }

    .gradio-container h1, .gradio-container h2, .gradio-container h3, 
    .gradio-container h4, .gradio-container h5, .gradio-container h6 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        margin-bottom: 16px !important;
    }

    .gradio-container p, .gradio-container div, .gradio-container span {
        color: var(--text-primary) !important;
    }

    /* Light mode card section headers */
    .card-header {
        background: var(--background-color);
        margin: -32px -32px 24px -32px;
        padding: 20px 32px;
        border-bottom: 1px solid var(--border-color);
        border-radius: var(--border-radius) var(--border-radius) 0 0;
    }

    .card-header h3 {
        margin: 0 !important;
        color: var(--text-primary) !important;
        font-size: 1.125rem !important;
        font-weight: 700 !important;
    }

    /* Light mode chart containers */
    .chart-container {
        background: var(--card-background) !important;
        border-radius: var(--border-radius-small) !important;
        padding: 20px !important;
        box-shadow: var(--card-shadow) !important;
        margin: 16px 0 !important;
        border: 1px solid var(--border-color) !important;
    }

    /* Modern grid layouts for light mode */
    .grid-container {
        display: grid;
        gap: 16px;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }

    .grid-item {
        background: var(--card-background);
        border-radius: var(--border-radius-small);
        padding: 20px;
        box-shadow: var(--card-shadow);
        border: 1px solid var(--border-color);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .grid-item:hover {
        box-shadow: var(--card-shadow-hover);
        transform: translateY(-1px);
    }

    /* Light mode badges and indicators */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }

    .status-badge.success {
        background: var(--success-color);
        color: white;
    }

    .status-badge.warning {
        background: var(--warning-color);
        color: white;
    }

    .status-badge.danger {
        background: var(--danger-color);
        color: white;
    }

    .status-badge.info {
        background: var(--info-color);
        color: white;
    }

    /* Ensure tab content is visible */
    .gradio-container .tab-content {
        background: transparent !important;
    }

    /* Radio button and checkbox styling for light mode */
    .gradio-container .gr-radio input[type="radio"],
    .gradio-container .gr-checkbox input[type="checkbox"] {
        accent-color: var(--primary-color) !important;
    }

    /* Light mode loading states */
    .loading-indicator {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid var(--border-color);
        border-radius: 50%;
        border-top-color: var(--primary-color);
        animation: spin 1s ease-in-out infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    /* Light mode responsive design */
    @media (max-width: 768px) {
        .gradio-container {
            padding: 16px !important;
        }
        
        .main-title {
            font-size: 2.5rem !important;
        }
        
        .main-header {
            padding: 32px 24px !important;
        }
        
        .professional-card {
            padding: 24px !important;
            margin: 16px 0 !important;
        }
        
        .action-button {
            padding: 10px 20px !important;
            font-size: 13px !important;
        }
        
        .tab-nav button {
            padding: 10px 16px !important;
            font-size: 13px !important;
            margin: 0 2px !important;
        }
    }

    /* Professional accordion styling for light mode */
    .professional-accordion {
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius-small) !important;
        overflow: hidden !important;
        margin: 16px 0 !important;
        background: var(--card-background) !important;
    }

    .professional-accordion summary {
        background: var(--background-color) !important;
        padding: 16px !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        cursor: pointer !important;
        transition: background 0.2s ease !important;
        border-bottom: 1px solid var(--border-color) !important;
    }

    .professional-accordion summary:hover {
        background: var(--card-background) !important;
    }

    .professional-accordion[open] summary {
        border-bottom: 1px solid var(--border-color) !important;
    }
    </style>
    """
    
    with gr.Blocks(theme="default", title="FiFTO INDEX Option Selling", css=custom_css) as demo:
        # Professional Header
        gr.HTML("""
        <div class="main-header">
            <div class="main-title">📊 FiFTO INDEX Option Selling</div>
            <div class="subtitle">Professional Options Trading Analysis Platform</div>
        </div>
        """)
        
        analysis_data_state, summary_filepath_state, hedge_filepath_state, payoff_filepath_state = gr.State(), gr.State(), gr.State(), gr.State()
        
        def get_trade_tags_for_dropdown():
            trades = load_trades()
            if not trades: return gr.Dropdown(choices=[], label="Select Trade Group to Close", interactive=False)
            tags = sorted(list(set(t.get('entry_tag') for t in trades if t.get('entry_tag'))))
            return gr.Dropdown(choices=tags, label="Select Trade Group to Close", interactive=True)

        with gr.Tabs(elem_classes="tab-container"):
            with gr.TabItem("🎯 Strategy Generator", elem_classes="professional-card"):
                gr.HTML('<div class="info-panel"><strong>📈 Generate Professional Option Selling Strategies</strong><br/>Create data-driven strategies based on zone analysis and market conditions</div>')
                
                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Group():
                            gr.HTML('<h3 style="color: #1976D2; margin-bottom: 15px;">📊 Market Parameters</h3>')
                            with gr.Row():
                                index_dropdown = gr.Dropdown(
                                    ["NIFTY", "BANKNIFTY"], 
                                    label="📈 Select Index", 
                                    value="NIFTY",
                                    elem_classes="professional-input"
                                )
                                calc_dropdown = gr.Dropdown(
                                    ["Weekly", "Monthly"], 
                                    label="📅 Calculation Period", 
                                    value="Weekly",
                                    elem_classes="professional-input"
                                )
                            expiry_dropdown = gr.Dropdown(
                                label="📆 Expiry Date", 
                                info="⏳ Loading available expiries...", 
                                interactive=False,
                                elem_classes="professional-input"
                            )
                            hedge_premium_slider = gr.Slider(
                                5.0, 25.0, 10.0, 
                                step=1.0, 
                                label="🛡️ Hedge Premium % (of Sold Premium)",
                                elem_classes="professional-input"
                            )
                    
                    with gr.Column(scale=1):
                        gr.HTML('<h3 style="color: #1976D2; margin-bottom: 15px;">🚀 Actions</h3>')
                        run_button = gr.Button(
                            "🎯 Generate Strategy", 
                            variant="primary", 
                            size="lg",
                            elem_classes="action-button primary-button"
                        )
                        reset_button = gr.Button(
                            "🔄 Reset Analysis", 
                            elem_classes="action-button secondary-button"
                        )
                
                status_textbox_gen = gr.Textbox(
                    label="📊 Analysis Status", 
                    interactive=False,
                    elem_classes="status-display"
                )
                
                gr.HTML('<h3 style="color: #1976D2; margin-top: 20px;">📈 Generated Analysis Charts</h3>')
                with gr.Tabs():
                    with gr.TabItem("📊 Strategy Overview"):
                        output_summary_image = gr.Image(label="Strategy Summary", show_label=False)
                    with gr.TabItem("🛡️ Hedge Positions"):
                        output_hedge_image = gr.Image(label="Hedge Strategy", show_label=False)
                    with gr.TabItem("💰 P&L Analysis"):
                        output_payoff_image = gr.Image(label="Payoff Chart", show_label=False)
                
                with gr.Row():
                    add_button = gr.Button(
                        "➕ Add to Portfolio", 
                        elem_classes="action-button primary-button"
                    )
                    telegram_button = gr.Button(
                        "📱 Send to Telegram", 
                        elem_classes="action-button secondary-button"
                    )
            
            with gr.TabItem("💼 Portfolio Management", elem_classes="professional-card"):
                gr.HTML('<div class="info-panel"><strong>📊 Active Portfolio Monitoring</strong><br/>Monitor your active trades, manage positions, and track performance in real-time</div>')
                
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.HTML('<h3 style="color: #1976D2;">🎯 Group Position Management</h3>')
                        gr.Markdown("**Close entire trade groups** (e.g., all Monday Selling positions)")
                        group_close_dropdown = gr.Dropdown(
                            choices=[], 
                            label="🏷️ Select Trade Group to Close", 
                            interactive=False,
                            elem_classes="professional-input"
                        )
                    with gr.Column(scale=1):
                        gr.HTML('<h3 style="color: #1976D2;">⚡ Quick Actions</h3>')
                        group_close_button = gr.Button(
                            "🔴 Close Selected Group", 
                            variant="primary",
                            elem_classes="action-button danger-button"
                        )
                
                gr.HTML('<h3 style="color: #1976D2; margin-top: 20px;">📈 Active Positions</h3>')
                analysis_df = gr.DataFrame(
                    load_trades_for_display, 
                    label="Live Portfolio Tracking", 
                    every=60, 
                    interactive=False,
                    elem_classes="professional-table"
                )
                
                status_active_analysis = gr.Textbox(
                    label="📊 Portfolio Status", 
                    interactive=False,
                    elem_classes="status-display"
                )
                
                gr.HTML('<h3 style="color: #1976D2; margin-top: 15px;">🔧 Portfolio Actions</h3>')
                with gr.Row(): 
                    refresh_button = gr.Button(
                        "🔄 Refresh Data", 
                        elem_classes="action-button secondary-button"
                    )
                    clear_old_trades_button = gr.Button(
                        "🧹 Clear Expired", 
                        elem_classes="action-button secondary-button"
                    )
                    clear_all_trades_button = gr.Button(
                        "⚠️ Clear ALL Positions", 
                        elem_classes="action-button danger-button"
                    )
            
            with gr.TabItem("⚙️ Configuration", elem_classes="professional-card"):
                gr.HTML('<div class="info-panel"><strong>🔧 Platform Configuration</strong><br/>Configure monitoring settings, auto-generation schedules, and system preferences</div>')
                
                selected_schedule_id_hidden = gr.Textbox(visible=False)
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.HTML('<h3 style="color: #1976D2;">📊 P/L Monitoring</h3>')
                        settings_interval = gr.Radio(
                            ['15 Mins', '30 Mins', '1 Hour', 'Disable'], 
                            label="📈 P/L Summary Frequency", 
                            value=lambda: load_settings()['update_interval'],
                            elem_classes="professional-input"
                        )
                        save_monitoring_button = gr.Button(
                            "💾 Save P/L Settings", 
                            variant="primary",
                            elem_classes="action-button primary-button"
                        )
                    with gr.Column(scale=2):
                        gr.HTML('<h3 style="color: #1976D2;">⏰ Auto-Generation Schedules</h3>')
                        schedules_df = gr.DataFrame(
                            load_schedules_for_display, 
                            label="📅 Saved Schedules", 
                            interactive=True,
                            elem_classes="professional-table"
                        )
                        with gr.Accordion("➕ Add New Schedule", open=False, elem_classes="professional-accordion"):
                            with gr.Row():
                                new_schedule_days = gr.CheckboxGroup(
                                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
                                    label="🗓️ Run on Days",
                                    elem_classes="professional-input"
                                )
                                new_schedule_time = gr.Textbox(
                                    label="🕒 Run at Time (24H format, e.g., 09:20)", 
                                    value="09:20",
                                    elem_classes="professional-input"
                                )
                            with gr.Row():
                                new_schedule_index = gr.Dropdown(
                                    ["NIFTY", "BANKNIFTY"], 
                                    label="📊 Index", 
                                    value="NIFTY",
                                    elem_classes="professional-input"
                                )
                                new_schedule_calc = gr.Dropdown(
                                    ["Weekly", "Monthly"], 
                                    label="📋 Calculation Type", 
                                    value="Weekly",
                                    elem_classes="professional-input"
                                )
                        with gr.Row():
                            add_schedule_button = gr.Button(
                                "➕ Add Schedule", 
                                variant="primary",
                                elem_classes="action-button primary-button"
                            )
                            delete_schedule_button = gr.Button(
                                "🗑️ Delete Selected", 
                                interactive=False,
                                elem_classes="action-button danger-button"
                            )
                settings_status_box = gr.Textbox(
                    label="⚙️ Configuration Status", 
                    interactive=False,
                    elem_classes="status-display"
                )
        
        def update_analysis_tab_components():
            return load_trades_for_display(), get_trade_tags_for_dropdown()
        
        def handle_schedule_select(schedules_df, evt: gr.SelectData):
            if evt.index is None or evt.index[0] is None: return "", gr.Button(interactive=False)
            selected_id = schedules_df.iloc[evt.index[0]]['ID']
            return selected_id, gr.Button(interactive=True)

        run_event = run_button.click(fn=generate_analysis, inputs=[index_dropdown, calc_dropdown, expiry_dropdown, hedge_premium_slider], outputs=[output_summary_image, output_hedge_image, output_payoff_image, status_textbox_gen, analysis_data_state, summary_filepath_state, hedge_filepath_state, payoff_filepath_state])
        add_button.click(fn=add_to_analysis, inputs=[analysis_data_state], outputs=[status_textbox_gen, analysis_df]).then(fn=get_trade_tags_for_dropdown, outputs=[group_close_dropdown])
        telegram_button.click(fn=send_daily_chart_to_telegram, inputs=[summary_filepath_state, hedge_filepath_state, payoff_filepath_state, analysis_data_state], outputs=[status_textbox_gen])
        reset_button.click(lambda: (None, None, None, "Process stopped.", None, None, None, None), outputs=[output_summary_image, output_hedge_image, output_payoff_image, status_textbox_gen, analysis_data_state, summary_filepath_state, hedge_filepath_state, payoff_filepath_state], cancels=[run_event])
        
        group_close_button.click(fn=close_trade_group_by_tag, inputs=[group_close_dropdown, analysis_df], outputs=[analysis_df, status_active_analysis]).then(fn=get_trade_tags_for_dropdown, outputs=[group_close_dropdown])
        refresh_button.click(fn=update_analysis_tab_components, outputs=[analysis_df, group_close_dropdown])
        clear_old_trades_button.click(fn=clear_old_trades, outputs=[analysis_df, status_active_analysis]).then(fn=get_trade_tags_for_dropdown, outputs=[group_close_dropdown])
        clear_all_trades_button.click(fn=clear_all_trades, outputs=[analysis_df, status_active_analysis]).then(fn=get_trade_tags_for_dropdown, outputs=[group_close_dropdown])
        
        index_dropdown.change(fn=update_expiry_dates, inputs=index_dropdown, outputs=expiry_dropdown)
        save_monitoring_button.click(fn=update_monitoring_interval, inputs=[settings_interval], outputs=[settings_status_box])
        add_schedule_button.click(fn=add_new_schedule, inputs=[new_schedule_days, new_schedule_time, new_schedule_index, new_schedule_calc], outputs=[schedules_df, settings_status_box])
        schedules_df.select(fn=handle_schedule_select, inputs=[schedules_df], outputs=[selected_schedule_id_hidden, delete_schedule_button])
        delete_schedule_button.click(fn=delete_schedule_by_id, inputs=[selected_schedule_id_hidden], outputs=[schedules_df, settings_status_box]).then(lambda: ("", gr.Button(interactive=False)), outputs=[selected_schedule_id_hidden, delete_schedule_button])
        
        demo.load(fn=update_expiry_dates, inputs=index_dropdown, outputs=expiry_dropdown).then(fn=get_trade_tags_for_dropdown, outputs=[group_close_dropdown])
    return demo

if __name__ == "__main__":
    print("=== FiFTO Selling Analysis Tool ===")
    print("Initializing scheduler...")
    sync_scheduler_with_settings()
    app_settings = load_settings()
    interval_str, job_kwargs, is_paused = app_settings.get("update_interval", "15 Mins"), {}, False
    if interval_str == "Disable": is_paused = True; job_kwargs['minutes'] = 15
    else: value, unit = map(str.strip, interval_str.split()); job_kwargs['minutes' if unit == 'Mins' else 'hours'] = int(value)
    scheduler.add_job(send_pl_summary, 'interval', **job_kwargs, id='pl_summary')
    scheduler.add_job(check_for_ts_hits, 'interval', minutes=1, id='ts_checker')
    scheduler.add_job(lambda: send_pl_summary(is_eod_report=True), 'cron', day_of_week='mon-fri', hour=15, minute=45, id='eod_report')
    
    scheduler.start()
    if is_paused: scheduler.pause_job('pl_summary')
    atexit.register(lambda: scheduler.shutdown())
    
    print("🚀 FiFTO Analysis Tool Started Successfully!")
    print("📊 Background jobs scheduled:")
    print(f"   - P/L Summary: {interval_str}")
    print("   - Target/Stoploss Check: Every 1 minute")
    print("   - EOD Report: Weekdays at 3:45 PM")
    print("\n💡 Core functions available:")
    print("   - Options analysis and zone calculation")
    print("   - Telegram notifications")
    print("   - Trade monitoring and alerts")
    print("   - Scheduled auto-generation")
    
    print("\n🌐 Launching Gradio web interface...")
    try:
        demo = build_ui()
        # Try different ports if 7860 is busy
        for port in range(7860, 7870):
            try:
                demo.queue()  # Enable queue for Gradio 3.x
                demo.launch(
                    server_name="127.0.0.1",
                    server_port=port,
                    inbrowser=True,
                    share=False,
                    quiet=False
                )
                break
            except Exception as port_error:
                if port == 7869:  # Last port tried
                    raise port_error
                continue
    except Exception as e:
        print(f"❌ Could not launch web interface: {e}")
        print("✅ Running in background mode instead...")
        try:
            import time
            while True:
                time.sleep(60)  # Sleep for 1 minute intervals
        except KeyboardInterrupt:
            print("\n🛑 Shutting down FiFTO Analysis Tool...")
            scheduler.shutdown()
            print("✅ Application stopped successfully.")