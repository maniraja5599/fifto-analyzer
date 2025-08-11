# analyzer/utils.py

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf
import math, time, json, os, pytz, uuid
from datetime import datetime, timedelta
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
        "bot_token": "7981319366:AAG4mfNVjIyRSehitfkxQTN9D63d1EJMaa8",
        "chat_id": "-1002639599677",
        "enable_target_alerts": True,
        "enable_stoploss_alerts": True,
        "auto_close_targets": False,
        "auto_close_stoploss": False,
        "enable_trade_alerts": True,
        "enable_bulk_alerts": True,
        "enable_summary_alerts": True,
        # Lot size configuration
        "nifty_lot_size": 75,
        "banknifty_lot_size": 35,
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
    """Save settings with better error handling and validation."""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        
        # Validate settings data
        if not isinstance(settings_data, dict):
            raise ValueError("Settings data must be a dictionary")
        
        # Write to file with proper error handling
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f, indent=4)
        
        print(f"Settings saved successfully to: {SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        raise e

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
def get_lot_size(instrument):
    """Get the correct lot size for different instruments from settings."""
    settings = load_settings()
    lot_sizes = {
        "NIFTY": settings.get("nifty_lot_size", 75),
        "BANKNIFTY": settings.get("banknifty_lot_size", 35),
    }
    return lot_sizes.get(instrument, 50)  # Default to 50 if instrument not found

def round_to_nearest_50(value):
    """Round a value to the nearest 50 for cleaner target/stoploss amounts."""
    return round(value / 50) * 50

def calculate_weekly_zones(instrument_name, calculation_type):
    """
    Calculate weekly/monthly supply/demand zones using advanced logic from your provided Python file.
    Implements multiple fallback mechanisms and robust error handling.
    Returns supply_zone and demand_zone for strike selection.
    """
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    
    if instrument_name not in TICKERS:
        return None, None
        
    ticker_symbol = TICKERS[instrument_name]
    
    try:
        print(f"Calculating {calculation_type} zones for {instrument_name}...")
        
        # Try multiple approaches for data fetching (from your selling.py logic)
        df_zones = None
        
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
                return None, None
            
            current_price = option_chain_data['records']['underlyingValue']
            print(f"Current price from option chain: {current_price}")
            
            # Use simple percentage-based zones as fallback
            supply_zone = current_price * 1.02  # 2% above current price
            demand_zone = current_price * 0.98  # 2% below current price
            print(f"Using fallback zones - Supply: {supply_zone}, Demand: {demand_zone}")
            return supply_zone, demand_zone
        else:
            # Original zone calculation with fetched data
            df_zones.index = pd.to_datetime(df_zones.index)
            period_rule = 'W' if calculation_type == "Weekly" else 'ME'
            agg_df = df_zones.resample(period_rule).agg({
                'Open': 'first', 
                'High': 'max', 
                'Low': 'min'
            }).dropna()
            
            if agg_df.empty:
                print("Aggregated data is empty, using fallback zones...")
                option_chain_data = get_option_chain_data(instrument_name)
                if not option_chain_data: 
                    return None, None
                current_price = option_chain_data['records']['underlyingValue']
                supply_zone = current_price * 1.02
                demand_zone = current_price * 0.98
                return supply_zone, demand_zone
            else:
                base = agg_df['Open']
                rng5 = (agg_df['High'] - agg_df['Low']).rolling(min(5, len(agg_df))).mean()
                rng10 = (agg_df['High'] - agg_df['Low']).rolling(min(10, len(agg_df))).mean()
                latest_zones = pd.DataFrame({
                    'u1': base + 0.5*rng5, 
                    'u2': base + 0.5*rng10, 
                    'l1': base - 0.5*rng5, 
                    'l2': base - 0.5*rng10
                }).dropna()
                
                if latest_zones.empty:
                    print("Zone calculation failed, using fallback...")
                    option_chain_data = get_option_chain_data(instrument_name)
                    if not option_chain_data: 
                        return None, None
                    current_price = option_chain_data['records']['underlyingValue']
                    supply_zone = current_price * 1.02
                    demand_zone = current_price * 0.98
                    return supply_zone, demand_zone
                else:
                    latest_zone_data = latest_zones.iloc[-1]
                    supply_zone = round(max(latest_zone_data['u1'], latest_zone_data['u2']), 2)
                    demand_zone = round(min(latest_zone_data['l1'], latest_zone_data['l2']), 2)
                    
                    print(f"✅ {calculation_type} zones calculated for {instrument_name}:")
                    print(f"   Supply Zone: ₹{supply_zone}")
                    print(f"   Demand Zone: ₹{demand_zone}")
                    
                    return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ Error calculating weekly zones for {instrument_name}: {e}")
        return None, None

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

def find_hedge_strike(sold_strike, target_premium, options_data, option_type):
    """Find hedge strike from selling.py logic"""
    candidates = []
    for strike, price in options_data.items():
        is_valid_direction = (option_type == 'CE' and strike > sold_strike) or (option_type == 'PE' and strike < sold_strike)
        if is_valid_direction and strike % 100 == 0:
            candidates.append({'strike': strike, 'price': price, 'diff': abs(price - target_premium)})
    return min(candidates, key=lambda x: x['diff'])['strike'] if candidates else None

def calculate_hedge_positions(ce_strike, pe_strike, ce_price, pe_price, options_data):
    """
    Calculate hedge positions for sell strategy using 10% premium rule
    """
    # Calculate 10% of sell premiums for hedge target
    ce_hedge_target = ce_price * 0.10
    pe_hedge_target = pe_price * 0.10
    
    # Find best hedge strikes
    ce_hedge_strike = find_hedge_strike(ce_strike, ce_hedge_target, options_data['CE'], 'CE')
    pe_hedge_strike = find_hedge_strike(pe_strike, pe_hedge_target, options_data['PE'], 'PE')
    
    # Get hedge prices
    ce_hedge_price = options_data['CE'].get(ce_hedge_strike, 0) if ce_hedge_strike else 0
    pe_hedge_price = options_data['PE'].get(pe_hedge_strike, 0) if pe_hedge_strike else 0
    
    return {
        'ce_hedge_strike': ce_hedge_strike,
        'pe_hedge_strike': pe_hedge_strike,
        'ce_hedge_price': ce_hedge_price,
        'pe_hedge_price': pe_hedge_price,
        'total_hedge_premium': ce_hedge_price + pe_hedge_price
    }

# In analyzer/utils.py

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

def send_telegram_message(message="", image_paths=None):
    """Send message and/or images to Telegram."""
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

def send_trade_alert(trade_action, trade_data, additional_message=""):
    """Send trade-related alerts to Telegram."""
    if trade_action == "added":
        message = f"""🆕 *New Trade Added*
        
Trade ID: `{trade_data['id']}`
Instrument: {trade_data['instrument']}
Strategy: {trade_data['reward_type']}
Expiry: {trade_data['expiry']}
CE Strike: {trade_data['ce_strike']}
PE Strike: {trade_data['pe_strike']}
Premium: ₹{trade_data['initial_premium']:.2f}
Target: ₹{trade_data['target_amount']:.2f}
Stop Loss: ₹{trade_data['stoploss_amount']:.2f}
Tag: {trade_data.get('entry_tag', 'General')}

{additional_message}"""
    
    elif trade_action == "deleted":
        message = f"""🗑️ *Trade Deleted*
        
Trade ID: `{trade_data['id']}`
Strategy: {trade_data['reward_type']}
Status: {trade_data.get('status', 'Running')}

{additional_message}"""
    
    elif trade_action == "bulk_deleted":
        message = f"""🗑️ *Bulk Delete Operation*
        
{len(trade_data)} trades have been deleted.

{additional_message}"""
    
    elif trade_action == "closed":
        message = f"""✅ *Trade Manually Closed*
        
Trade ID: `{trade_data['id']}`
Strategy: {trade_data['reward_type']}
Final Status: Manually Closed

{additional_message}"""
    
    elif trade_action == "bulk_closed":
        message = f"""✅ *Bulk Close Operation*
        
{len(trade_data)} trades have been manually closed.

{additional_message}"""
    
    elif trade_action == "target_hit":
        message = f"""🎯 *TARGET HIT!*
        
Trade ID: `{trade_data['id']}`
Strategy: {trade_data['reward_type']}
Profit: ₹{additional_message}

Congratulations! 🎉"""
    
    elif trade_action == "stoploss_hit":
        message = f"""⛔ *STOP LOSS HIT*
        
Trade ID: `{trade_data['id']}`
Strategy: {trade_data['reward_type']}
Loss: ₹{additional_message}

Please review and adjust strategy if needed."""
    
    else:
        message = f"Trade Update: {trade_action}"
    
    return send_telegram_message(message)

def check_target_stoploss_alerts():
    """Check all active trades for target/stoploss alerts."""
    trades = load_trades()
    active_trades = [t for t in trades if t.get('status') == 'Running']
    
    if not active_trades:
        return
    
    alerts_sent = 0
    
    # Group trades by instrument for efficient API calls
    instrument_groups = defaultdict(list)
    for trade in active_trades:
        instrument_groups[trade['instrument']].append(trade)
    
    for instrument, trades_in_group in instrument_groups.items():
        chain = get_option_chain_data(instrument)
        if not chain:
            continue
            
        lot_size = get_lot_size(instrument)
        
        for trade in trades_in_group:
            current_ce, current_pe = 0.0, 0.0
            
            for item in chain['records']['data']:
                if item.get("expiryDate") == trade['expiry']:
                    if item.get("strikePrice") == trade['ce_strike'] and item.get("CE"):
                        current_ce = item["CE"]["lastPrice"]
                    if item.get("strikePrice") == trade['pe_strike'] and item.get("PE"):
                        current_pe = item["PE"]["lastPrice"]
            
            if current_ce == 0.0 and current_pe == 0.0:
                continue
            
            # Calculate current P&L
            pnl = (trade['initial_premium'] - (current_ce + current_pe)) * lot_size
            
            # Check for target hit
            if pnl >= trade['target_amount']:
                trade['status'] = 'Target'
                trade['final_pnl'] = pnl
                trade['closed_date'] = datetime.now().isoformat()
                send_trade_alert("target_hit", trade, f"{pnl:.2f}")
                alerts_sent += 1
            
            # Check for stoploss hit  
            elif pnl <= -trade['stoploss_amount']:
                trade['status'] = 'Stoploss'
                trade['final_pnl'] = pnl
                trade['closed_date'] = datetime.now().isoformat()
                send_trade_alert("stoploss_hit", trade, f"{pnl:.2f}")
                alerts_sent += 1
    
    # Save any status changes
    if alerts_sent > 0:
        save_trades(trades)
    
    return alerts_sent

def generate_payoff_chart(strategies_df, lot_size, current_price, instrument_name, zone_label, expiry_label):
    """Generate a clean enterprise-style payoff diagram with hedge positions included."""
    # Price range for payoff calculation
    price_range = np.linspace(current_price * 0.85, current_price * 1.15, 300)
    
    strategy = strategies_df.iloc[0]
    ce_strike, pe_strike = strategy['CE Strike'], strategy['PE Strike']
    ce_hedge_strike, pe_hedge_strike = strategy['CE Hedge Strike'], strategy['PE Hedge Strike']
    
    # Calculate net premium (sell premium - hedge premium)
    net_premium = strategy['Net Premium']
    
    # Calculate payoff for hedged short straddle/strangle
    # Sell premium from CE and PE, buy hedge positions
    sell_ce_pnl = -np.maximum(price_range - ce_strike, 0)  # Short CE
    sell_pe_pnl = -np.maximum(pe_strike - price_range, 0)  # Short PE
    buy_ce_hedge_pnl = np.maximum(price_range - ce_hedge_strike, 0)  # Long CE hedge
    buy_pe_hedge_pnl = np.maximum(pe_hedge_strike - price_range, 0)  # Long PE hedge
    
    # Total P&L = Net Premium + Sell Positions + Hedge Positions
    pnl = (net_premium + sell_ce_pnl + sell_pe_pnl + buy_ce_hedge_pnl + buy_pe_hedge_pnl) * lot_size
    
    # Calculate max profit and breakeven points using net premium
    max_profit = net_premium * lot_size
    be_lower = pe_strike - net_premium
    be_upper = ce_strike + net_premium
    
    # Create clean enterprise chart with expanded size for external text
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(16, 9), facecolor='white')
    ax.set_facecolor('white')
    
    # Adjust subplot to make room for external text
    plt.subplots_adjust(right=0.75)
    
    # Plot payoff line with thinner line styling
    ax.plot(price_range, pnl, color='#2563eb', linewidth=2, label='Hedged Payoff', alpha=0.9)
    
    # Fill profit/loss areas with clean colors
    ax.fill_between(price_range, pnl, 0, where=(pnl >= 0), 
                    color='#16a34a', alpha=0.2, label='Profit Zone', interpolate=True)
    ax.fill_between(price_range, pnl, 0, where=(pnl < 0), 
                    color='#dc2626', alpha=0.2, label='Loss Zone', interpolate=True)
    
    # Add hedge strike lines
    ax.axvline(x=ce_hedge_strike, color='#7c3aed', linestyle=':', alpha=0.7, linewidth=1.5,
               label=f'CE Hedge: {ce_hedge_strike:.0f}')
    ax.axvline(x=pe_hedge_strike, color='#7c3aed', linestyle=':', alpha=0.7, linewidth=1.5,
               label=f'PE Hedge: {pe_hedge_strike:.0f}')
    
    # Add breakeven lines with thinner styling
    ax.axvline(x=be_lower, color='#f59e0b', linestyle='--', alpha=0.8, linewidth=1.5,
               label=f'Lower BE: {be_lower:.0f}')
    ax.axvline(x=be_upper, color='#f59e0b', linestyle='--', alpha=0.8, linewidth=1.5,
               label=f'Upper BE: {be_upper:.0f}')
    
    # Add current price line with thinner styling
    ax.axvline(x=current_price, color='#1e293b', linestyle='-', alpha=0.9, linewidth=2,
               label=f'Current: {current_price:.0f}')
    
    # Zero line
    ax.axhline(y=0, color='#64748b', linestyle='-', alpha=0.4, linewidth=1)
    
    # Highlight max profit point with better positioning
    mid_point = (pe_strike + ce_strike) / 2
    ax.scatter([mid_point], [max_profit], color='#16a34a', s=100, zorder=5, 
              edgecolor='white', linewidth=2)
    
    # Position annotation to avoid overlap - adjust based on chart position
    annotation_offset_y = 20 if max_profit > 0 else -30
    ax.annotate(f'₹{max_profit:.0f}', 
               xy=(mid_point, max_profit), xytext=(0, annotation_offset_y),
               textcoords='offset points', color='#16a34a', fontweight='bold',
               fontsize=10, ha='center', va='center',
               arrowprops=dict(arrowstyle='->', color='#16a34a', alpha=0.7, lw=1.5),
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                        edgecolor='#16a34a', alpha=0.9, linewidth=1))
    
    # Professional title and labels - centered
    ax.set_title(f'{instrument_name} Payoff Analysis - {expiry_label}', 
                fontsize=16, fontweight='bold', color='#1e293b', pad=20)
    ax.set_xlabel('Price at Expiry (₹)', fontsize=12, color='#374151', fontweight='600')
    ax.set_ylabel('Profit/Loss (₹)', fontsize=12, color='#374151', fontweight='600')
    
    # Clean grid
    ax.grid(True, alpha=0.3, linestyle='-', color='#e5e7eb', linewidth=0.8)
    ax.set_axisbelow(True)
    
    # Calculate auto-adjusted Y-axis limits based on data
    min_pnl = min(pnl)
    max_pnl = max(pnl)
    y_margin = max(abs(min_pnl), abs(max_pnl)) * 0.1  # 10% margin
    y_min = min_pnl - y_margin
    y_max = max_pnl + y_margin
    
    # Set auto-adjusted Y-axis limits
    ax.set_ylim(y_min, y_max)
    
    # Auto-adjust X-axis for better view
    x_margin = (current_price * 0.15 - current_price * 0.85) * 0.05  # 5% margin
    ax.set_xlim(current_price * 0.85 - x_margin, current_price * 1.15 + x_margin)
    
    # Professional title and labels - with better spacing
    ax.set_title(f'{instrument_name} Payoff Analysis - {expiry_label}', 
                fontsize=16, fontweight='bold', color='#1e293b', pad=30)
    ax.set_xlabel('Price at Expiry (₹)', fontsize=12, color='#374151', fontweight='600')
    ax.set_ylabel('Profit/Loss (₹)', fontsize=12, color='#374151', fontweight='600')
    
    # Clean grid
    ax.grid(True, alpha=0.3, linestyle='-', color='#e5e7eb', linewidth=0.8)
    ax.set_axisbelow(True)
    
    # Style legend with better positioning - move to upper left to avoid overlap
    legend = ax.legend(loc='upper left', fancybox=True, shadow=False, 
                      frameon=True, facecolor='white', edgecolor='#e5e7eb',
                      fontsize=10, framealpha=0.95)
    legend.get_frame().set_linewidth(1)
    for text in legend.get_texts():
        text.set_color('#374151')
    
    # Clean tick styling
    ax.tick_params(colors='#6b7280', which='both', labelsize=10)
    for spine in ax.spines.values():
        spine.set_color('#d1d5db')
        spine.set_linewidth(1)
    
    # Improved statistics box positioning - move to upper right, outside plot area
    hedge_cost = strategy.get('CE Hedge Price', 0) + strategy.get('PE Hedge Price', 0)
    sell_premium = strategy.get('Sell Premium', 0)
    stats_text = f'''Sell Premium: ₹{sell_premium:.2f}
Hedge Cost: ₹{hedge_cost:.2f}
Net Premium: ₹{net_premium:.2f}
Max Profit: ₹{max_profit:.0f}
Breakeven: {be_lower:.0f} - {be_upper:.0f}
Max Loss: Limited by Hedge'''
    
    ax.text(1.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10, ha='left',
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#f8fafc', 
                     alpha=0.95, edgecolor='#e2e8f0', linewidth=1),
            color='#334155')
    
    # Move FiFTO branding to bottom right, outside plot area
    ax.text(1.02, 0.02, "FiFTO Analytics", transform=ax.transAxes, ha='left', va='bottom',
            fontsize=10, color='#16a34a', fontweight='bold', alpha=0.8)
    
    # Save chart with expanded bbox to include external text
    filename = f"payoff_{uuid.uuid4().hex}.png"
    filepath = os.path.join(STATIC_FOLDER_PATH, filename)
    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', 
                edgecolor='none', pad_inches=0.5)
    plt.close(fig)
    
    return f'static/{filename}'  # Return the relative path for web access

def generate_analysis(instrument_name, calculation_type, selected_expiry_str):
    if not selected_expiry_str or "Loading..." in selected_expiry_str or "Error" in selected_expiry_str:
        return None, "Expiry Date has not loaded. Please wait or re-select the Index to try again."
    
    try:
        TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        print("Initializing...")
        
        # Use correct lot sizes as specified by user: NIFTY=75, BANKNIFTY=35
        lot_size = get_lot_size(instrument_name)
        strike_increment = 50 if instrument_name == "NIFTY" else 100
        ticker_symbol = TICKERS[instrument_name]
        
        print(f"Calculating {calculation_type} zones...")
        
        # Try multiple approaches for data fetching (exact logic from selling.py)
        df_zones = None
        
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
                return None, f"Error: Unable to fetch data for {instrument_name}. Please try again later."
            
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
            agg_df = df_zones.resample(period_rule).agg({
                'Open': 'first', 
                'High': 'max', 
                'Low': 'min'
            }).dropna()
            
            if agg_df.empty:
                print("Aggregated data is empty, using fallback zones...")
                option_chain_data = get_option_chain_data(instrument_name)
                if not option_chain_data: 
                    return None, f"Error: Unable to fetch data for {instrument_name}."
                current_price = option_chain_data['records']['underlyingValue']
                supply_zone = current_price * 1.02
                demand_zone = current_price * 0.98
            else:
                base = agg_df['Open']
                rng5 = (agg_df['High'] - agg_df['Low']).rolling(min(5, len(agg_df))).mean()
                rng10 = (agg_df['High'] - agg_df['Low']).rolling(min(10, len(agg_df))).mean()
                latest_zones = pd.DataFrame({
                    'u1': base + 0.5*rng5, 
                    'u2': base + 0.5*rng10, 
                    'l1': base - 0.5*rng5, 
                    'l2': base - 0.5*rng10
                }).dropna()
                
                if latest_zones.empty:
                    print("Zone calculation failed, using fallback...")
                    option_chain_data = get_option_chain_data(instrument_name)
                    if not option_chain_data: 
                        return None, f"Error: Unable to fetch data for {instrument_name}."
                    current_price = option_chain_data['records']['underlyingValue']
                    supply_zone = current_price * 1.02
                    demand_zone = current_price * 0.98
                else:
                    latest_zone_data = latest_zones.iloc[-1]
                    supply_zone = round(max(latest_zone_data['u1'], latest_zone_data['u2']), 2)
                    demand_zone = round(min(latest_zone_data['l1'], latest_zone_data['l2']), 2)
        
        print("Fetching option chain...")
        option_chain_data = get_option_chain_data(instrument_name)
        if not option_chain_data: 
            return None, f"Error fetching option chain."
        
        current_price = option_chain_data['records']['underlyingValue']
    expiry_label = datetime.strptime(selected_expiry_str, '%d-%b-%Y').strftime("%d-%b")
    
    if option_chain_data:
        # Extract real data from API
        ce_prices, pe_prices = {}, {}
        for item in option_chain_data['records']['data']:
            if item.get("expiryDate") == selected_expiry_str:
                if item.get("CE"): ce_prices[item['strikePrice']] = item["CE"]["lastPrice"]
                if item.get("PE"): pe_prices[item['strikePrice']] = item["PE"]["lastPrice"]
        debug_log(f"📊 Real API data - CE: {len(ce_prices)}, PE: {len(pe_prices)} strikes")
    
    # Zone-based strike selection (matching selling.py logic exactly)
    if supply_zone is not None and demand_zone is not None:
        debug_log("📊 Using zone-based strike selection")
        
        # CE strikes based on supply zone - exactly from selling.py
        ce_high = math.ceil(supply_zone / strike_increment) * strike_increment
        strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
        
        # PE strikes based on demand zone - exactly from selling.py  
        pe_high = math.floor(demand_zone / strike_increment) * strike_increment
        candidate_puts = sorted([s for s in pe_prices if s < pe_high and pe_prices.get(s, 0) > 0], 
                               key=lambda s: pe_prices.get(s, 0), reverse=True)
        pe_mid = (candidate_puts[0] if candidate_puts else pe_high - strike_increment)
        pe_low = (candidate_puts[1] if len(candidate_puts) > 1 else 
                 (candidate_puts[0] if candidate_puts else pe_high - strike_increment) - strike_increment)
        strikes_pe = [pe_high, pe_mid, pe_low]
        
        debug_log(f"📊 Zone-based strikes:")
        debug_log(f"   CE strikes (from supply ₹{supply_zone}): {strikes_ce}")
        debug_log(f"   PE strikes (from demand ₹{demand_zone}): {strikes_pe}")
        
    else:
        debug_log("📊 Using fallback current price-based strike selection")
        
        # Fallback to current price-based selection
        ce_high = math.ceil(current_price / strike_increment) * strike_increment
        strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
        pe_high = math.floor(current_price / strike_increment) * strike_increment
        candidate_puts = sorted([s for s in pe_prices if s < pe_high and pe_prices.get(s, 0) > 0], 
                               key=lambda s: pe_prices.get(s, 0), reverse=True)
        pe_mid = (candidate_puts[0] if candidate_puts else pe_high - strike_increment)
        pe_low = (candidate_puts[1] if len(candidate_puts) > 1 else pe_mid - strike_increment)
        strikes_pe = [pe_high, pe_mid, pe_low]
    
    # Find suitable hedge strikes - exact logic from selling.py
    debug_log("Finding suitable hedges...")
    temp_df = pd.DataFrame({
        "CE Strike": strikes_ce, 
        "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce], 
        "PE Strike": strikes_pe, 
        "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe]
    })
    
    hedge_premium_decimal = 10.0 / 100.0  # Default 10% hedge premium
    strikes_ce_hedge, strikes_pe_hedge = [], []
    
    for _, row in temp_df.iterrows():
        ce_hedge = find_hedge_strike(row['CE Strike'], row['CE Price'] * hedge_premium_decimal, ce_prices, 'CE')
        pe_hedge = find_hedge_strike(row['PE Strike'], row['PE Price'] * hedge_premium_decimal, pe_prices, 'PE')
        
        print(f"🔍 CE Strike: {row['CE Strike']}, Price: {row['CE Price']}, Target: {row['CE Price'] * hedge_premium_decimal:.2f}, Found Hedge: {ce_hedge}")
        print(f"🔍 PE Strike: {row['PE Strike']}, Price: {row['PE Price']}, Target: {row['PE Price'] * hedge_premium_decimal:.2f}, Found Hedge: {pe_hedge}")
        
        strikes_ce_hedge.append(ce_hedge or row['CE Strike'] + 1000)
        strikes_pe_hedge.append(pe_hedge or row['PE Strike'] - 1000)
    
    # Create comprehensive DataFrame with hedge data - matching selling.py structure  
    df = pd.DataFrame({
        "Entry": ["High Reward", "Mid Reward", "Low Reward"], 
        "CE Strike": strikes_ce, 
        "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce], 
        "PE Strike": strikes_pe, 
        "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe],
        "CE Hedge Strike": strikes_ce_hedge,
        "CE Hedge Price": [ce_prices.get(s, 0.0) for s in strikes_ce_hedge],
        "PE Hedge Strike": strikes_pe_hedge, 
        "PE Hedge Price": [pe_prices.get(s, 0.0) for s in strikes_pe_hedge]
    })
    
    df["Combined Premium"] = df["CE Price"] + df["PE Price"]
    df["Net Premium"] = (df["CE Price"] + df["PE Price"]) - (df["CE Hedge Price"] + df["PE Hedge Price"])
    
    # Calculate target and stoploss using Net Premium - matching selling.py
    df["Target"] = (df["Net Premium"] * 0.80 * lot_size).round(2)
    df["Stoploss"] = (df["Net Premium"] * 0.80 * lot_size).round(2)
    
    # Create comprehensive display DataFrame for chart including hedge data
    display_df = df[['Entry', 'CE Strike', 'CE Price', 'CE Hedge Strike', 'CE Hedge Price', 
                     'PE Strike', 'PE Price', 'PE Hedge Strike', 'PE Hedge Price', 
                     'Combined Premium', 'Net Premium']].copy()
    display_df['Total Hedge'] = df['CE Hedge Price'] + df['PE Hedge Price']
    display_df['Target/SL'] = (df["Net Premium"] * 0.80 * lot_size).round(2)
    display_df.rename(columns={
        'Combined Premium': 'Sell Premium',
        'CE Hedge Strike': 'CE Hedge',
        'PE Hedge Strike': 'PE Hedge',
        'CE Hedge Price': 'CE H.Price',
        'PE Hedge Price': 'PE H.Price'
    }, inplace=True)
    
    # Debug: Log the DataFrame data
    print(f"📊 DataFrame created with shape: {df.shape}")
    print(f"📊 DataFrame columns: {list(df.columns)}")
    print(f"📊 Sample DataFrame data:")
    print(df.to_string())
    print(f"📊 Display DataFrame: \n{display_df.to_string()}")
    print(f"📊 CE Prices found: {len(ce_prices)} items")
    print(f"📊 PE Prices found: {len(pe_prices)} items")
    
    title, zone_label = f"FiFTO - {calculation_type} {instrument_name} Selling", calculation_type
    summary_filename = f"summary_{uuid.uuid4().hex}.png"
    summary_filepath = os.path.join(STATIC_FOLDER_PATH, summary_filename)
    
    plt.style.use('default')  # Use clean default style
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('white')
    ax.axis('off')
    
    # Professional title with global theme styling
    fig.suptitle(f'{instrument_name} Options Analysis - {expiry_label}', 
                fontsize=18, fontweight='bold', y=0.94, color='#1e293b', ha='center')
    
    # Enhanced info box with global theme styling
    info_text = f"{instrument_name}: ₹{current_price}\nExpiry: {expiry_label}\nGenerated: {datetime.now().strftime('%d-%b-%Y %H:%M')}"
    ax.text(0.5, 0.85, info_text, transform=ax.transAxes, ha='center', va='center', 
            fontsize=12, fontfamily='monospace', color='#1e293b', fontweight='600',
            bbox=dict(boxstyle='round,pad=0.8', facecolor='#f1f5f9', 
                     edgecolor='#2563eb', linewidth=1.5, alpha=0.95))
    
    # Create professional table with global UI styling
    table = plt.table(cellText=display_df.values, 
                     colLabels=display_df.columns,
                     colColours=['#2563eb'] * len(display_df.columns),  # Professional blue header
                     cellLoc='center', 
                     loc='center',
                     bbox=[0.05, 0.25, 0.9, 0.45])
    
    # Style the table to match global UI theme
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)  # Better row height
    
    # Header styling - matching Bootstrap primary theme
    for col in range(len(display_df.columns)):
        cell = table[(0, col)]
        cell.get_text().set_color('white')
        cell.get_text().set_fontweight('bold')
        cell.set_facecolor('#2563eb')  # Professional blue matching our theme
        cell.set_text_props(fontsize=11)
        cell.set_edgecolor('#1d4ed8')  # Darker blue border
        cell.set_linewidth(1.5)
    
    # Data cell styling with clean alternating colors matching global theme
    for row in range(1, len(display_df) + 1):
        for col in range(len(display_df.columns)):
            cell = table[(row, col)]
            # Match our global clean card colors
            if row % 2 == 0:
                cell.set_facecolor('#f8fafc')  # Light gray-blue like our cards
            else:
                cell.set_facecolor('#ffffff')  # Pure white
            
            # Text styling matching global theme
            cell.get_text().set_color('#1e293b')  # Dark text matching our headings
            cell.get_text().set_fontweight('600')  # Semi-bold like our table data
            cell.set_edgecolor('#e2e8f0')  # Light border matching our cards
            cell.set_linewidth(1)
            
            # Add special styling for numeric columns
            # Columns: Entry, CE Strike, CE Price, CE Hedge, CE H.Price, PE Strike, PE Price, PE Hedge, PE H.Price, Sell Premium, Total Hedge, Net Premium, Target/SL
            numeric_cols = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # All except Entry
            if col in numeric_cols:
                cell.get_text().set_fontfamily('monospace')  # Monospace for numbers
                cell.get_text().set_fontweight('bold')
                
                # Special coloring for different types
                if col in [3, 7]:  # Hedge strike columns (CE Hedge, PE Hedge)
                    cell.get_text().set_color('#7c3aed')  # Purple for hedge strikes
                elif col in [4, 8]:  # Hedge price columns (CE H.Price, PE H.Price)
                    cell.get_text().set_color('#7c3aed')  # Purple for hedge prices
                elif col == 10:  # Total Hedge column
                    cell.get_text().set_color('#dc2626')  # Red for hedge cost
                elif col == 11:  # Net Premium column
                    cell.get_text().set_color('#059669')  # Green for net premium
                elif col == 12:  # Target/SL column
                    cell.get_text().set_color('#16a34a')  # Green for target amounts
                    # Format target values as integers since they're rounded to 50
                    current_text = cell.get_text().get_text()
                    if current_text and current_text.replace('.', '').isdigit():
                        cell.get_text().set_text(f"₹{int(float(current_text))}")
    
    # Enhanced footer with global theme styling
    first_row = df.iloc[0]  # Get first strategy row
    footer_text = f"Hedged Strategy: Net Premium ₹{first_row['Net Premium']:.2f} (Sell: ₹{first_row['Combined Premium']:.2f} - Hedge: ₹{first_row['CE Hedge Price'] + first_row['PE Hedge Price']:.2f})"
    ax.text(0.5, 0.15, footer_text, transform=ax.transAxes, ha='center', va='center',
            fontsize=12, fontweight='bold', color='#16a34a',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#f0fdf4', 
                     edgecolor='#16a34a', alpha=0.8, linewidth=1))
    
    # Clean disclaimer with global theme
    # Clean disclaimer with global theme
    ax.text(0.5, 0.06, "For educational purposes only", 
            transform=ax.transAxes, ha='center', va='center',
            fontsize=9, color='#64748b', style='italic')
    
    # Centered FiFTO branding with enhanced styling
    ax.text(0.5, 0.02, "FiFTO Analytics", transform=ax.transAxes, ha='center', va='center',
            fontsize=11, color='#16a34a', fontweight='bold', alpha=0.9)
    
    plt.savefig(summary_filepath, dpi=150, bbox_inches='tight', facecolor='white', 
                edgecolor='none', pad_inches=0.3)
    plt.close(fig)
    payoff_filepath = generate_payoff_chart(df, lot_size, current_price, instrument_name, zone_label, expiry_label)
    
    # Create enhanced HTML table for web display with hedge information
    table_html = f"""
    <div class="table-responsive">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th scope="col">Entry</th>
                    <th scope="col">CE Strike</th>
                    <th scope="col">CE Price</th>
                    <th scope="col">CE Hedge</th>
                    <th scope="col">PE Strike</th>
                    <th scope="col">PE Price</th>
                    <th scope="col">PE Hedge</th>
                    <th scope="col">Net Premium</th>
                    <th scope="col">Target/SL</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, row in display_df.iterrows():
        table_html += f"""
                <tr>
                    <td><strong>{row['Entry']}</strong></td>
                    <td>{row['CE Strike']}</td>
                    <td>₹{row['CE Price']:.2f}</td>
                    <td><span class="badge bg-secondary">{row['CE Hedge']}</span></td>
                    <td>{row['PE Strike']}</td>
                    <td>₹{row['PE Price']:.2f}</td>
                    <td><span class="badge bg-secondary">{row['PE Hedge']}</span></td>
                    <td><span class="badge bg-info">₹{row['Net Premium']:.2f}</span></td>
                    <td><span class="badge bg-success">₹{row['Target/SL']:.0f}</span></td>
                </tr>
        """
    
    table_html += """
            </tbody>
        </table>
    </div>
    """
    
    analysis_data = {
        "instrument": instrument_name, 
        "expiry": selected_expiry_str, 
        "lot_size": lot_size, 
        "df_data": df.to_dict('records'), 
        "summary_file": f'static/{summary_filename}', 
        "payoff_file": payoff_filepath, 
        "display_df_html": table_html,
        "supply_zone": supply_zone,
        "demand_zone": demand_zone,
        "zone_based": supply_zone is not None and demand_zone is not None
    }
    
    debug_log(f"✅ Analysis completed successfully for {instrument_name}")
    debug_log(f"Generated files: {summary_filename}, {payoff_filepath}")
    
    # Create status message based on whether zones were used
    if supply_zone is not None and demand_zone is not None:
        status_message = f"✅ {calculation_type} analysis completed with supply/demand zones (Supply: ₹{supply_zone:.0f}, Demand: ₹{demand_zone:.0f})"
    else:
        status_message = f"✅ {calculation_type} analysis completed with price-based strike selection"
    
    return analysis_data, status_message

# --- Trade Action Functions ---
def add_to_analysis(analysis_data):
    print("🔍 ADD_TO_ANALYSIS DEBUG START")
    print(f"📊 Analysis data received: {analysis_data is not None}")
    
    if not analysis_data or not analysis_data.get('df_data'): 
        print("❌ No analysis data or df_data")
        return "Generate an analysis first."
    
    print(f"📈 df_data entries: {len(analysis_data.get('df_data', []))}")
    print(f"📋 Sample df_data: {analysis_data.get('df_data', [])[:1]}")
    
    trades = load_trades()
    print(f"📊 Existing trades: {len(trades)}")
    
    # Show existing trade IDs for debugging
    if trades:
        print("🔍 Existing trade IDs:")
        for trade in trades:
            print(f"   - {trade.get('id', 'NO_ID')}")
    
    new_trades_added = 0
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    day_name = datetime.now().strftime("%A")
    entry_tag = f"{day_name} Selling"
    
    # Add timestamp to make trade IDs more unique
    timestamp_suffix = datetime.now().strftime("%H%M")
    
    print(f"🏷️ Entry tag: {entry_tag}")
    print(f"⏰ Timestamp suffix: {timestamp_suffix}")
    
    for i, entry in enumerate(analysis_data['df_data']):
        print(f"\n🔄 Processing entry {i+1}: {entry}")
        
        # Check if the entry has the required fields
        if 'Entry' not in entry:
            print(f"❌ Missing 'Entry' field in entry: {entry}")
            continue
            
        # Generate more unique trade ID with timestamp
        base_id = f"{analysis_data['instrument']}_{analysis_data['expiry']}_{entry['Entry'].replace(' ', '')}"
        trade_id = f"{base_id}_{timestamp_suffix}"
        print(f"🆔 Generated trade ID: {trade_id}")
        
        # Check for duplicates
        existing_trade = any(t['id'] == trade_id for t in trades)
        print(f"🔍 Duplicate check: {existing_trade}")
        
        if existing_trade: 
            print(f"⚠️ Skipping duplicate trade: {trade_id}")
            # Try without timestamp for backward compatibility
            fallback_id = base_id
            if not any(t['id'] == fallback_id for t in trades):
                trade_id = fallback_id
                print(f"🔄 Using fallback ID: {trade_id}")
            else:
                print(f"❌ Both IDs exist, skipping")
                continue
            
        # Create trade object with hedge position data
        new_trade = {
            "id": trade_id, 
            "start_time": start_time, 
            "status": "Running", 
            "entry_tag": entry_tag, 
            "instrument": analysis_data['instrument'], 
            "expiry": analysis_data['expiry'], 
            "reward_type": entry['Entry'], 
            "ce_strike": entry.get('CE Strike', 0), 
            "pe_strike": entry.get('PE Strike', 0), 
            "initial_premium": entry.get('Combined Premium', 0), 
            "target_amount": entry.get('Target', 0), 
            "stoploss_amount": entry.get('Stoploss', 0),
            # Hedge position data for sell strategies
            "ce_hedge_strike": entry.get('CE Hedge Strike', 0),
            "pe_hedge_strike": entry.get('PE Hedge Strike', 0),
            "ce_hedge_price": entry.get('CE Hedge Price', 0),
            "pe_hedge_price": entry.get('PE Hedge Price', 0),
            "net_premium": entry.get('Net Premium', entry.get('Combined Premium', 0)),
            "total_hedge_premium": entry.get('CE Hedge Price', 0) + entry.get('PE Hedge Price', 0)
        }
        
        print(f"✅ Adding trade: {new_trade}")
        trades.append(new_trade)
        new_trades_added += 1
    
    print(f"💾 Saving {len(trades)} total trades ({new_trades_added} new)")
    save_trades(trades)
    
    # Verify the save worked
    saved_trades = load_trades()
    print(f"✅ Verification: {len(saved_trades)} trades now in file")
    
    result = f"Added {new_trades_added} new trade(s) tagged as '{entry_tag}'."
    print(f"📝 Result: {result}")
    print("🔍 ADD_TO_ANALYSIS DEBUG END\n")
    
    return result

def auto_add_to_portfolio(analysis_data, auto_tag="Auto Generated"):
    """
    Automatically add generated charts to portfolio for trades that weren't manually added.
    This function is called when automation generates charts and they need to be added to active trades.
    """
    if not analysis_data or not analysis_data.get('df_data'):
        return "No analysis data to add to portfolio."
    
    trades = load_trades()
    new_trades_added = 0
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Check if any trades from this analysis already exist
    existing_trade_ids = {t['id'] for t in trades}
    
    for entry in analysis_data['df_data']:
        trade_id = f"{analysis_data['instrument']}_{analysis_data['expiry']}_{entry['Entry'].replace(' ', '')}"
        
        # Only add if this specific trade doesn't already exist
        if trade_id not in existing_trade_ids:
            new_trade = {
                "id": trade_id,
                "start_time": start_time,
                "status": "Running",
                "entry_tag": auto_tag,
                "instrument": analysis_data['instrument'],
                "expiry": analysis_data['expiry'],
                "reward_type": entry['Entry'],
                "ce_strike": entry['CE Strike'],
                "pe_strike": entry['PE Strike'],
                "initial_premium": entry['Combined Premium'],
                "target_amount": entry['Target'],
                "stoploss_amount": entry['Stoploss'],
                "auto_added": True  # Flag to identify auto-added trades
            }
            trades.append(new_trade)
            new_trades_added += 1
    
    if new_trades_added > 0:
        save_trades(trades)
        
        # Send Telegram notification about auto-added trades
        notification_message = f"""🤖 *Auto Portfolio Update*

📊 Generated charts automatically added to portfolio:
- Instrument: {analysis_data['instrument']}
- Expiry: {analysis_data['expiry']}
- Trades Added: {new_trades_added}
- Tag: {auto_tag}

These trades are now being monitored for target/stoploss alerts."""
        
        send_telegram_message(notification_message)
        
        return f"✅ Auto-added {new_trades_added} trade(s) to portfolio with tag '{auto_tag}'"
    else:
        return "No new trades to add - all strategies already exist in portfolio."

def generate_and_auto_add_analysis(instrument_name, calculation_type, selected_expiry_str, auto_add=True):
    """
    Generate analysis and optionally auto-add to portfolio.
    This is used by automation to ensure generated charts are always added to active trades.
    """
    # Generate the analysis first
    analysis_data, status_message = generate_analysis(instrument_name, calculation_type, selected_expiry_str)
    
    if analysis_data and auto_add:
        # Check if user hasn't manually added these trades
        trades = load_trades()
        manual_trade_exists = False
        
        for entry in analysis_data['df_data']:
            trade_id = f"{analysis_data['instrument']}_{analysis_data['expiry']}_{entry['Entry'].replace(' ', '')}"
            # Check if trade exists and was manually added (doesn't have auto_added flag)
            for trade in trades:
                if trade['id'] == trade_id and not trade.get('auto_added', False):
                    manual_trade_exists = True
                    break
            if manual_trade_exists:
                break
        
        if not manual_trade_exists:
            # Auto-add to portfolio since user hasn't manually added
            auto_tag = f"Auto {datetime.now().strftime('%d-%b')} {instrument_name}"
            auto_add_result = auto_add_to_portfolio(analysis_data, auto_tag)
            
            # Combine status messages
            combined_status = f"{status_message}\n{auto_add_result}"
            return analysis_data, combined_status
    
    return analysis_data, status_message

def close_selected_trade(trade_id_to_close):
    all_trades = load_trades()
    trade_to_close = next((t for t in all_trades if t['id'] == trade_id_to_close), None)
    if not trade_to_close: 
        return
    
    # Calculate current P&L before closing
    current_pnl = trade_to_close.get('pnl', 0)
    
    # Mark trade as manually closed with P&L and timestamp
    trade_to_close['status'] = 'Manually Closed'
    trade_to_close['final_pnl'] = current_pnl
    trade_to_close['closed_date'] = datetime.now().isoformat()
    
    # Send notification with P&L information
    message = f"🔔 *Manual Square-Off Alert* 🔔\n\nTrade ID: `{trade_to_close['id']}`\nFinal P&L: ₹{current_pnl:.2f}\nStatus: Manually Closed"
    send_telegram_message(message)
    
    # Save updated trades (don't remove, just update status)
    save_trades(all_trades)

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
    return True

def run_automated_chart_generation():
    """
    Run automated chart generation based on configured settings.
    This function automatically generates charts and adds them to portfolio for users who haven't manually added them.
    """
    from django.utils import timezone
    import pytz
    
    settings = load_settings()
    
    # Check if auto-generation is enabled
    if not settings.get('enable_auto_generation', False):
        print("Auto-generation is disabled")
        return "Auto-generation is disabled"
    
    # System readiness check
    try:
        # Check if required settings exist
        required_settings = ['auto_gen_instruments', 'auto_gen_days', 'auto_gen_time']
        for setting in required_settings:
            if not settings.get(setting):
                print(f"Missing required setting: {setting}")
                return f"System not ready: Missing {setting} configuration"
        
        # Get current time in IST timezone
        ist_tz = pytz.timezone('Asia/Kolkata')
        current_time = timezone.now().astimezone(ist_tz)
        
        # Check market hours (9:15 AM to 3:30 PM IST on weekdays) - Only for notification
        market_open = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = current_time.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Determine market status for notification
        market_status = ""
        if current_time.weekday() >= 5:  # Weekend
            market_status = f"⚠️ WEEKEND: Market is closed - IST Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        elif current_time < market_open or current_time > market_close:
            market_status = f"⚠️ AFTER HOURS: Market is closed - IST Time: {current_time.strftime('%H:%M')}"
        else:
            market_status = f"✅ MARKET HOURS: Active trading time - IST Time: {current_time.strftime('%H:%M')}"
        
        print(market_status)
        # Continue execution regardless of market hours
            
    except Exception as e:
        print(f"System readiness check failed: {str(e)}")
        return f"System readiness check failed: {str(e)}"
    
    # Get automation settings
    auto_gen_instruments = settings.get('auto_gen_instruments', [])
    auto_gen_days = settings.get('auto_gen_days', [])
    auto_gen_time = settings.get('auto_gen_time', '09:20')
    nifty_calc_type = settings.get('nifty_calc_type', 'Weekly')
    banknifty_calc_type = settings.get('banknifty_calc_type', 'Monthly')
    
    # Run automation on ALL DAYS - Check day only for information
    today = current_time.strftime('%A').lower()
    if today not in [day.lower() for day in auto_gen_days]:
        day_status = f"📅 NON-SCHEDULED DAY: Today ({today}) is not in scheduled days ({auto_gen_days}) but running anyway"
        print(day_status)
    else:
        day_status = f"📅 SCHEDULED DAY: Today ({today}) is a scheduled day for auto-generation"
        print(day_status)
    
    # Enhanced time check with proper scheduling logic (using IST)
    schedule_hour, schedule_minute = map(int, auto_gen_time.split(':'))
    
    # Create scheduled time for today in IST
    scheduled_time = current_time.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
    
    # Check if we're within 15 minutes of scheduled time (to handle scheduler delays)
    time_diff = (current_time - scheduled_time).total_seconds() / 60  # minutes
    
    if time_diff < -15:  # More than 15 minutes before scheduled time
        print(f"Current IST time ({current_time.strftime('%H:%M')}) is before scheduled time ({auto_gen_time}) - waiting...")
        return f"Current IST time ({current_time.strftime('%H:%M')}) is before scheduled time ({auto_gen_time})"
    elif time_diff > 60:  # More than 1 hour after scheduled time
        print(f"Scheduled time ({auto_gen_time}) has passed by more than 1 hour - skipping for today")
        return f"Scheduled time ({auto_gen_time}) has passed by more than 1 hour - skipping for today"
    
    results = []
    
    # Generate expiry date (next Thursday for weekly, next month end for monthly)
    def get_next_expiry(calc_type):
        today = datetime.now()
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
            
            print(f"🤖 Auto-generating charts for {instrument} {calc_type} expiring {expiry}")
            
            # Use the updated chart generation function
            chart_result = generate_chart_for_instrument(instrument, calc_type)
            results.append(f"{instrument}: {chart_result}")
            print(f"Chart generation result: {chart_result}")
            
        except Exception as e:
            error_result = f"❌ {instrument}: Error - {str(e)}"
            results.append(error_result)
            print(error_result)
    
    # Prepare final result with market status notification
    if results:
        final_message = f"🤖 Automated Chart Generation Complete\n{market_status}\n" + "\n".join(results)
        
        # Send to Telegram if configured
        try:
            send_telegram_message(final_message)
            print("📱 Results sent to Telegram")
        except Exception as e:
            print(f"⚠️ Failed to send to Telegram: {str(e)}")
        
        return final_message
    else:
        no_instruments_message = f"🤖 Automation Run Complete\n{market_status}\nNo instruments selected for generation"
        send_telegram_message(no_instruments_message)
        return no_instruments_message

# In analyzer/utils.py

def monitor_trades(is_eod_report=False):
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Running trade monitoring...")
    trades = load_trades()
    if not trades:
        print("[*] No active trades to monitor.")
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
        lot_size = get_lot_size(instrument)

        for trade in trades_in_group:
            current_ce, current_pe = 0.0, 0.0
            current_ce_hedge, current_pe_hedge = 0.0, 0.0
            
            for item in chain['records']['data']:
                if item.get("expiryDate") == trade['expiry']:
                    # Get main position prices
                    if item.get("strikePrice") == trade['ce_strike'] and item.get("CE"):
                        current_ce = item["CE"]["lastPrice"]
                    if item.get("strikePrice") == trade['pe_strike'] and item.get("PE"):
                        current_pe = item["PE"]["lastPrice"]
                    
                    # Get hedge position prices
                    if item.get("strikePrice") == trade.get('ce_hedge_strike') and item.get("CE"):
                        current_ce_hedge = item["CE"]["lastPrice"]
                    if item.get("strikePrice") == trade.get('pe_hedge_strike') and item.get("PE"):
                        current_pe_hedge = item["PE"]["lastPrice"]

            if current_ce == 0.0 and current_pe == 0.0: continue

            # Calculate P&L based on whether position is hedged
            has_hedge = trade.get('ce_hedge_strike', 0) > 0 or trade.get('pe_hedge_strike', 0) > 0
            
            if has_hedge:
                # For hedged positions: Net P&L = (Sell Premium - Buy Premium) - (Current Sell - Current Buy)
                initial_sell_premium = trade.get('initial_premium', 0)
                initial_hedge_premium = trade.get('total_hedge_premium', 0)
                
                current_sell_premium = current_ce + current_pe
                current_hedge_premium = current_ce_hedge + current_pe_hedge
                
                pnl = ((initial_sell_premium - initial_hedge_premium) - (current_sell_premium - current_hedge_premium)) * lot_size
            else:
                # For non-hedged positions: Original logic
                pnl = (trade['initial_premium'] - (current_ce + current_pe)) * lot_size
                
            any_trade_updated = True

            tag_key = trade.get('entry_tag', 'General Trades')
            pl_data_for_image['tags'][tag_key].append({'reward_type': trade['reward_type'], 'pnl': pnl})

            # Check for Target or Stoploss
            if pnl >= trade['target_amount']:
                trade['status'] = 'Target'
                trade['final_pnl'] = pnl
                trade['closed_date'] = datetime.now().isoformat()
                msg = f"✅ TARGET HIT: {trade['id']} ({tag_key})\nP/L: ₹{pnl:.2f}"
                print(msg)
                send_telegram_message(msg)
            elif pnl <= -trade['stoploss_amount']:
                trade['status'] = 'Stoploss'
                trade['final_pnl'] = pnl
                trade['closed_date'] = datetime.now().isoformat()
                msg = f"❌ STOPLOSS HIT: {trade['id']} ({tag_key})\nP/L: ₹{pnl:.2f}"
                print(msg)
                send_telegram_message(msg)

    # Send periodic update image to Telegram
    if any_trade_updated and not is_eod_report:
        image_path = generate_pl_update_image(pl_data_for_image, now)
        send_telegram_message(message="", image_paths=[image_path])
        os.remove(image_path)
        print("[+] Sent P/L update to Telegram.")

    # Save any status changes
    save_trades(active_trades + completed_trades)

def test_specific_automation(automation_config):
    """Test a specific automation configuration."""
    try:
        print(f"[DEBUG] Testing automation: {automation_config['name']}")
        
        # Prepare test parameters
        test_instruments = automation_config.get('instruments', [])
        nifty_calc_type = automation_config.get('nifty_calc_type', 'Weekly')
        banknifty_calc_type = automation_config.get('banknifty_calc_type', 'Monthly')
        
        if not test_instruments:
            return "No instruments selected for testing"
        
        # Run chart generation for selected instruments
        result_messages = []
        
        if 'NIFTY' in test_instruments:
            print(f"[DEBUG] Generating NIFTY chart with {nifty_calc_type} calculation")
            nifty_result = generate_chart_for_instrument('NIFTY', nifty_calc_type)
            result_messages.append(f"NIFTY ({nifty_calc_type}): {nifty_result}")
        
        if 'BANKNIFTY' in test_instruments:
            print(f"[DEBUG] Generating BANKNIFTY chart with {banknifty_calc_type} calculation")
            banknifty_result = generate_chart_for_instrument('BANKNIFTY', banknifty_calc_type)
            result_messages.append(f"BANKNIFTY ({banknifty_calc_type}): {banknifty_result}")
        
        final_result = "\n".join(result_messages) if result_messages else "No charts generated"
        print(f"[DEBUG] Test automation completed: {final_result}")
        return final_result
        
    except Exception as e:
        error_msg = f"Test automation failed: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return error_msg

def generate_chart_for_instrument(instrument, calc_type):
    """Generate chart for a specific instrument and calculation type."""
    try:
        print(f"🚀 Starting chart generation for {instrument} with {calc_type} calculation")
        
        # Get next expiry date based on calculation type
        today = datetime.now()
        if calc_type == 'Weekly':
            # Find next Thursday
            days_ahead = 3 - today.weekday()  # Thursday is 3
            if days_ahead <= 0:  # Thursday already passed
                days_ahead += 7
            next_expiry = today + timedelta(days=days_ahead)
        else:  # Monthly
            # Find last Thursday of next month
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            last_day = (next_month + timedelta(days=31)).replace(day=1) - timedelta(days=1)
            last_thursday = last_day - timedelta(days=(last_day.weekday() - 3) % 7)
            next_expiry = last_thursday
        
        expiry_str = next_expiry.strftime('%d-%b-%Y')
        print(f"📅 Using expiry date: {expiry_str}")
        
        # Call the actual analysis function
        analysis_data, status_message = generate_analysis(instrument, calc_type, expiry_str)
        
        if analysis_data:
            print(f"✅ Chart generation successful for {instrument}")
            
            # Auto-add to portfolio if enabled
            try:
                settings = load_settings()
                if settings.get('auto_portfolio_enabled', False):
                    add_result = add_to_analysis(analysis_data)
                    print(f"📊 Auto-added to portfolio: {add_result}")
            except Exception as e:
                print(f"⚠️ Failed to auto-add to portfolio: {str(e)}")
            
            return f"✅ Chart generated successfully for {instrument} ({calc_type}) - {status_message}"
        else:
            print(f"❌ Chart generation failed for {instrument}: {status_message}")
            return f"❌ Failed to generate chart for {instrument}: {status_message}"
            
    except Exception as e:
        error_msg = f"❌ Chart generation error for {instrument}: {str(e)}"
        print(error_msg)
        return error_msg

def start_permanent_schedule(schedule):
    """Start a permanent schedule that runs daily until manually turned off."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        import atexit
        
        # Create or get the global scheduler
        if not hasattr(start_permanent_schedule, 'scheduler'):
            start_permanent_schedule.scheduler = BackgroundScheduler()
            start_permanent_schedule.scheduler.start()
            atexit.register(lambda: start_permanent_schedule.scheduler.shutdown())
        
        scheduler = start_permanent_schedule.scheduler
        job_id = f"permanent_schedule_{schedule['id']}"
        
        # Remove existing job if any
        try:
            scheduler.remove_job(job_id)
        except:
            pass
        
        # Schedule the job to run daily
        hour, minute = schedule['time'].split(':')
        scheduler.add_job(
            func=run_permanent_schedule,
            trigger='cron',
            hour=int(hour),
            minute=int(minute),
            id=job_id,
            args=[schedule],
            replace_existing=True
        )
        
        print(f"[+] Started permanent schedule '{schedule['name']}' at {schedule['time']} daily")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to start permanent schedule: {str(e)}")
        return False

def stop_permanent_schedule(schedule_id):
    """Stop a permanent schedule."""
    try:
        if hasattr(start_permanent_schedule, 'scheduler'):
            scheduler = start_permanent_schedule.scheduler
            job_id = f"permanent_schedule_{schedule_id}"
            scheduler.remove_job(job_id)
            print(f"[+] Stopped permanent schedule {schedule_id}")
            return True
    except Exception as e:
        print(f"[ERROR] Failed to stop permanent schedule {schedule_id}: {str(e)}")
        return False

def run_permanent_schedule(schedule):
    """Execute a permanent schedule."""
    try:
        print(f"[+] Running permanent schedule: {schedule['name']}")
        
        # Check if enabled
        if not schedule.get('enabled', False):
            print(f"[!] Schedule '{schedule['name']}' is disabled, skipping")
            return
        
        # Get current time and check market status
        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        
        # Check market hours for notification
        market_open = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = current_time.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Determine market status
        if current_time.weekday() >= 5:  # Weekend
            market_status = f"⚠️ WEEKEND: Market is closed"
        elif current_time < market_open or current_time > market_close:
            market_status = f"⚠️ AFTER HOURS: Market is closed"
        else:
            market_status = f"✅ MARKET HOURS: Active trading time"
        
        print(f"Market Status: {market_status}")
        
        # Generate charts for selected instruments
        results = []
        
        if 'NIFTY' in schedule.get('instruments', []):
            nifty_result = generate_chart_for_instrument('NIFTY', schedule.get('nifty_calc_type', 'Weekly'))
            results.append(f"NIFTY: {nifty_result}")
        
        if 'BANKNIFTY' in schedule.get('instruments', []):
            banknifty_result = generate_chart_for_instrument('BANKNIFTY', schedule.get('banknifty_calc_type', 'Monthly'))
            results.append(f"BANKNIFTY: {banknifty_result}")
        
        # Update schedule with last run information
        schedule['last_run'] = current_time.isoformat()
        if results:
            schedule['last_result'] = "Success: Charts generated"
        else:
            schedule['last_result'] = "No instruments selected"
        
        # Save updated schedule
        settings = load_settings()
        multiple_schedules = settings.get('multiple_schedules', [])
        for i, sched in enumerate(multiple_schedules):
            if sched.get('id') == schedule.get('id'):
                multiple_schedules[i] = schedule
                break
        settings['multiple_schedules'] = multiple_schedules
        save_settings(settings)
        
        # Send results to Telegram with market status
        if results:
            message = f"🤖 Automated Chart Generation - {schedule['name']}\n{market_status}\n" + "\n".join(results)
            send_telegram_message(message)
        else:
            message = f"🤖 Automated Schedule Run - {schedule['name']}\n{market_status}\nNo instruments selected for generation"
            send_telegram_message(message)
        
        print(f"[+] Completed permanent schedule: {schedule['name']}")
        
    except Exception as e:
        error_msg = f"[ERROR] Permanent schedule '{schedule['name']}' failed: {str(e)}"
        print(error_msg)
        
        # Update schedule with error information
        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        schedule['last_run'] = current_time.isoformat()
        schedule['last_result'] = f"Error: {str(e)}"
        
        # Save updated schedule
        try:
            settings = load_settings()
            multiple_schedules = settings.get('multiple_schedules', [])
            for i, sched in enumerate(multiple_schedules):
                if sched.get('id') == schedule.get('id'):
                    multiple_schedules[i] = schedule
                    break
            settings['multiple_schedules'] = multiple_schedules
            save_settings(settings)
        except:
            pass
        
        send_telegram_message(f"❌ Automation Error: {error_msg}")

def run_test_automation_now():
    """Run a quick test of automation system."""
    try:
        print(f"[DEBUG] Running quick automation test")
        
        # Test with default settings
        nifty_result = generate_chart_for_instrument('NIFTY', 'Weekly')
        banknifty_result = generate_chart_for_instrument('BANKNIFTY', 'Monthly')
        
        result = f"NIFTY (Weekly): {nifty_result}\nBANKNIFTY (Monthly): {banknifty_result}"
        print(f"[DEBUG] Quick test completed: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Quick test failed: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return error_msg

def add_automation_activity(title, description, status='success'):
    """Add an automation activity to recent activities log."""
    try:
        settings = load_settings()
        activities = settings.get('automation_activities', [])
        
        # Create new activity
        activity = {
            'title': title,
            'description': description,
            'status': status,
            'time': datetime.now().strftime('%d %b %Y, %I:%M %p'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add to beginning of list
        activities.insert(0, activity)
        
        # Keep only last 50 activities
        activities = activities[:50]
        
        # Save back to settings
        settings['automation_activities'] = activities
        save_settings(settings)
        
    except Exception as e:
        print(f"[ERROR] Failed to add automation activity: {str(e)}")

def get_recent_automation_activities(limit=10):
    """Get recent automation activities."""
    try:
        settings = load_settings()
        activities = settings.get('automation_activities', [])
        return activities[:limit]
    except Exception as e:
        print(f"[ERROR] Failed to get automation activities: {str(e)}")
        return []