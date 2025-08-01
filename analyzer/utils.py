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
    Calculate weekly supply/demand zones using the same logic from the original Python file.
    Returns supply_zone and demand_zone for strike selection.
    """
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    
    if instrument_name not in TICKERS:
        return None, None
        
    ticker_symbol = TICKERS[instrument_name]
    
    try:
        # Fetch historical data for zone calculation
        df_zones = yf.Ticker(ticker_symbol).history(period="5y", interval="1d")
        
        # Special handling for NIFTY Weekly as in original code
        if calculation_type == "Weekly" and instrument_name == "NIFTY":
            df_zones = yf.Ticker(ticker_symbol).history(period="6mo", interval="1d")
            
        if df_zones.empty:
            print(f"❌ Failed to fetch historical data for {instrument_name}")
            return None, None
            
        # Convert index to datetime
        df_zones.index = pd.to_datetime(df_zones.index)
        
        # Resample based on calculation type (Weekly/Monthly)
        resample_period = 'W' if calculation_type == "Weekly" else 'ME'
        agg_df = df_zones.resample(resample_period).agg({
            'Open': 'first', 
            'High': 'max', 
            'Low': 'min'
        }).dropna()
        
        # Calculate rolling ranges (5 and 10 periods)
        rng5 = (agg_df['High'] - agg_df['Low']).rolling(5).mean()
        rng10 = (agg_df['High'] - agg_df['Low']).rolling(10).mean()
        
        # Base price (Open)
        base = agg_df['Open']
        
        # Calculate supply and demand zones
        u1 = base + 0.5 * rng5  # Upper zone 1
        u2 = base + 0.5 * rng10  # Upper zone 2
        l1 = base - 0.5 * rng5   # Lower zone 1
        l2 = base - 0.5 * rng10  # Lower zone 2
        
        # Get the latest zones
        latest_zones = pd.DataFrame({
            'u1': u1, 
            'u2': u2, 
            'l1': l1, 
            'l2': l2
        }).dropna().iloc[-1]
        
        # Calculate supply and demand zones
        supply_zone = round(max(latest_zones['u1'], latest_zones['u2']), 2)
        demand_zone = round(min(latest_zones['l1'], latest_zones['l2']), 2)
        
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
    """Generate a clean enterprise-style payoff diagram with professional styling."""
    # Price range for payoff calculation
    price_range = np.linspace(current_price * 0.85, current_price * 1.15, 300)
    
    strategy = strategies_df.iloc[0]
    ce_strike, pe_strike, premium = strategy['CE Strike'], strategy['PE Strike'], strategy['Combined Premium']
    
    # Calculate payoff for short straddle/strangle with max loss limit
    pnl = (premium - np.maximum(price_range - ce_strike, 0) - np.maximum(pe_strike - price_range, 0)) * lot_size
    
    # Limit maximum loss to -15000
    pnl = np.maximum(pnl, -15000)
    
    # Calculate max profit and breakeven points
    max_profit = premium * lot_size
    be_lower = pe_strike - premium
    be_upper = ce_strike + premium
    
    # Create clean enterprise chart with expanded size for external text
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(16, 9), facecolor='white')
    ax.set_facecolor('white')
    
    # Adjust subplot to make room for external text
    plt.subplots_adjust(right=0.75)
    
    # Plot payoff line with thinner line styling
    ax.plot(price_range, pnl, color='#2563eb', linewidth=2, label='Payoff Curve', alpha=0.9)
    
    # Fill profit/loss areas with clean colors
    ax.fill_between(price_range, pnl, 0, where=(pnl >= 0), 
                    color='#16a34a', alpha=0.2, label='Profit Zone', interpolate=True)
    ax.fill_between(price_range, pnl, 0, where=(pnl < 0), 
                    color='#dc2626', alpha=0.2, label='Loss Zone', interpolate=True)
    
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
    stats_text = f'''Max Profit: ₹{max_profit:.0f}
Breakeven: {be_lower:.0f} - {be_upper:.0f}
Max Loss: ₹{min_pnl:.0f}'''
    
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
    # Create a debug log file
    debug_file = r"C:\Users\manir\Desktop\debug_log.txt"
    
    def debug_log(message):
        with open(debug_file, 'a', encoding='utf-8') as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] UTILS: {message}\n")
        print(f"UTILS: {message}")  # Also print to console
    
    debug_log(f"=== generate_analysis() called ===")
    debug_log(f"Parameters: instrument={instrument_name}, calc_type={calculation_type}, expiry={selected_expiry_str}")
    
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    if not all([instrument_name, calculation_type, selected_expiry_str]):
        debug_log("❌ Missing required parameters")
        return None, "Please select valid inputs."
    
    ticker_symbol = TICKERS[instrument_name]
    debug_log(f"Using ticker symbol: {ticker_symbol}")
    
    lot_size = get_lot_size(instrument_name)
    strike_increment = 50 if instrument_name == "NIFTY" else 100
    
    # Calculate weekly supply/demand zones using the original logic
    debug_log(f"📊 Calculating {calculation_type} supply/demand zones...")
    supply_zone, demand_zone = calculate_weekly_zones(instrument_name, calculation_type)
    
    if supply_zone is None or demand_zone is None:
        debug_log("❌ Failed to calculate zones, using fallback method")
        # Fallback to simple price-based method
        supply_zone = None
        demand_zone = None
    else:
        debug_log(f"✅ Zones calculated - Supply: ₹{supply_zone}, Demand: ₹{demand_zone}")
    
    zone_label = calculation_type
    
    # Add error handling for option chain fetch
    print("📡 Fetching option chain data...")
    try:
        option_chain_data = get_option_chain_data(instrument_name)
        if option_chain_data:
            print("✅ Option chain data fetched successfully")
        else:
            print("❌ Option chain data is None")
    except Exception as e:
        print(f"❌ Exception fetching option chain: {e}")
        return None, f"Error fetching option chain: {e}"
    
    if not option_chain_data:
        print("❌ No option chain data available - using sample data for testing")
        # Use sample data for testing when API fails
        current_price = 24750 if instrument_name == "NIFTY" else 51500
        ce_prices = {24800: 45.5, 24850: 35.2, 24900: 26.8}
        pe_prices = {24700: 42.3, 24650: 33.1, 24600: 25.7}
        debug_log("🔄 Using sample data due to API unavailability")
    else:
        try:
            current_price = option_chain_data['records']['underlyingValue']
        except Exception as e:
            return None, f"Error reading underlying value: {e}"
    expiry_label = datetime.strptime(selected_expiry_str, '%d-%b-%Y').strftime("%d-%b")
    
    if option_chain_data:
        # Extract real data from API
        ce_prices, pe_prices = {}, {}
        for item in option_chain_data['records']['data']:
            if item.get("expiryDate") == selected_expiry_str:
                if item.get("CE"): ce_prices[item['strikePrice']] = item["CE"]["lastPrice"]
                if item.get("PE"): pe_prices[item['strikePrice']] = item["PE"]["lastPrice"]
        debug_log(f"📊 Real API data - CE: {len(ce_prices)}, PE: {len(pe_prices)} strikes")
    
    # Zone-based strike selection (using supply/demand zones)
    if supply_zone is not None and demand_zone is not None:
        debug_log("📊 Using zone-based strike selection")
        
        # CE strikes based on supply zone (resistance)
        ce_high = math.ceil(supply_zone / strike_increment) * strike_increment
        strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
        
        # PE strikes based on demand zone (support)
        pe_high = math.floor(demand_zone / strike_increment) * strike_increment
        
        # Select best PE strikes below demand zone with highest premiums
        candidate_puts = sorted([s for s in pe_prices if s < pe_high and pe_prices.get(s, 0) > 0], 
                               key=lambda s: pe_prices.get(s, 0), reverse=True)
        
        pe_mid = (candidate_puts[0] if candidate_puts else pe_high - strike_increment)
        pe_low = (candidate_puts[1] if len(candidate_puts) > 1 else pe_mid - strike_increment)
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
    df = pd.DataFrame({"Entry": ["High Reward", "Mid Reward", "Low Reward"], "CE Strike": strikes_ce, "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce], "PE Strike": strikes_pe, "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe]})
    df["Combined Premium"] = df["CE Price"] + df["PE Price"]
    
    # Calculate target and stoploss with global round-off by 50
    df["Target"] = df["Combined Premium"].apply(lambda x: round_to_nearest_50((x * 0.80 * lot_size)))
    df["Stoploss"] = df["Combined Premium"].apply(lambda x: round_to_nearest_50((x * 0.80 * lot_size)))
    
    display_df = df[['Entry', 'CE Strike', 'CE Price', 'PE Strike', 'PE Price']].copy()
    # Format target/SL values as integers since they're rounded to 50
    display_df['Target/SL (1:1)'] = df['Target'].apply(lambda x: f"₹{int(x)}")
    
    # Debug: Log the DataFrame data
    debug_log(f"📊 DataFrame created with shape: {df.shape}")
    debug_log(f"📊 Display DataFrame: \n{display_df.to_string()}")
    debug_log(f"📊 CE Prices found: {len(ce_prices)} items")
    debug_log(f"📊 PE Prices found: {len(pe_prices)} items")
    
    title, zone_label = f"FiFTO - {calculation_type} {instrument_name} Selling", calculation_type
    summary_filename = f"summary_{uuid.uuid4().hex}.png"
    summary_filepath = os.path.join(STATIC_FOLDER_PATH, summary_filename)
    
    # Create clean enterprise-style analysis chart
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
            
            # Add special styling for numeric columns (prices and targets)
            if col in [2, 4, 5]:  # Price and Target columns
                cell.get_text().set_fontfamily('monospace')  # Monospace for numbers
                cell.get_text().set_fontweight('bold')
                if col == 5:  # Target/SL column - format as integer since rounded to 50
                    cell.get_text().set_color('#16a34a')  # Green for target amounts
                    # Format target values as integers since they're rounded to 50
                    current_text = cell.get_text().get_text()
                    if current_text and current_text.replace('.', '').isdigit():
                        cell.get_text().set_text(f"₹{int(float(current_text))}")
    
    # Enhanced footer with global theme styling
    footer_text = f"Risk Management: 1:1 Target/SL Ratio"
    ax.text(0.5, 0.15, footer_text, transform=ax.transAxes, ha='center', va='center',
            fontsize=12, fontweight='bold', color='#16a34a',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#f0fdf4', 
                     edgecolor='#16a34a', alpha=0.8, linewidth=1))
    
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
    
    # Create enhanced HTML table for web display
    table_html = f"""
    <div class="table-responsive">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th scope="col">Entry</th>
                    <th scope="col">CE Strike</th>
                    <th scope="col">CE Price</th>
                    <th scope="col">PE Strike</th>
                    <th scope="col">PE Price</th>
                    <th scope="col">Target/SL (1:1)</th>
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
                    <td>{row['PE Strike']}</td>
                    <td>₹{row['PE Price']:.2f}</td>
                    <td><span class="badge bg-success">{row['Target/SL (1:1)']}</span></td>
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