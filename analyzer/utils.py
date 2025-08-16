# analyzer/utils.py

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import requests
import math, time, json, os, pytz, uuid
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from django.conf import settings

# Primary data sources - YFinance for chart analysis and zone calculations
import yfinance as yf

# NSE Data Integration for current prices only
try:
    from .nse_data import get_alternative_nse_data
    from .nse_enhanced import get_enhanced_nse_data
    NSE_AVAILABLE = True
    print("✅ NSE data modules loaded successfully for current prices")
except ImportError as e:
    print(f"⚠️  NSE data modules not available: {e}. Using yfinance fallback.")
    NSE_AVAILABLE = False

# --- Configuration Paths ---
BASE_DIR_USER = os.path.expanduser('~') # User's home directory for data files
TRADES_DB_FILE = os.path.join(BASE_DIR_USER, "active_trades.json")
SETTINGS_FILE = os.path.join(BASE_DIR_USER, "app_settings.json")
EXPIRY_CACHE_FILE = os.path.join(BASE_DIR_USER, "expiry_cache.json")
OPTION_CHAIN_CACHE_FILE = os.path.join(BASE_DIR_USER, "option_chain_cache.json")
TRADES_DATA_CACHE_FILE = os.path.join(BASE_DIR_USER, "trades_data_cache.json")
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

# --- Expiry Date Cache Management ---
def load_expiry_cache():
    """Load cached expiry dates."""
    if not os.path.exists(EXPIRY_CACHE_FILE):
        return {}
    try:
        with open(EXPIRY_CACHE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_expiry_cache(cache_data):
    """Save expiry dates cache."""
    try:
        with open(EXPIRY_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving expiry cache: {e}")
        return False

def is_thursday():
    """Check if today is Thursday."""
    return datetime.now().weekday() == 3  # Thursday is 3

def should_refresh_expiry_cache():
    """Check if expiry cache should be refreshed (every Thursday)."""
    cache = load_expiry_cache()
    last_refresh = cache.get('last_refresh')
    
    if not last_refresh:
        return True
    
    try:
        last_refresh_date = datetime.fromisoformat(last_refresh).date()
        today = datetime.now().date()
        
        # Refresh if it's Thursday and we haven't refreshed today
        if is_thursday() and last_refresh_date < today:
            return True
            
        # Also refresh if it's been more than a week
        if (today - last_refresh_date).days > 7:
            return True
            
        return False
    except:
        return True

def get_cached_expiry_dates(instrument):
    """Get cached expiry dates for instrument."""
    cache = load_expiry_cache()
    return cache.get(instrument, {}).get('expiry_dates', [])

def update_expiry_cache(instrument, expiry_dates):
    """Update expiry cache for instrument."""
    cache = load_expiry_cache()
    
    if instrument not in cache:
        cache[instrument] = {}
    
    cache[instrument]['expiry_dates'] = expiry_dates
    cache[instrument]['cached_on'] = datetime.now().isoformat()
    cache['last_refresh'] = datetime.now().isoformat()
    
    save_expiry_cache(cache)
    print(f"✅ Updated expiry cache for {instrument}: {len(expiry_dates)} dates")

def round_to_nearest_50(value):
    """Round a value to the nearest 50 for cleaner target/stoploss amounts."""
    return round(value / 50) * 50

def calculate_weekly_zones(instrument_name, calculation_type):
    """
    Calculate weekly supply/demand zones using direct yfinance implementation
    This replicates the exact working method from 09:55:04 PM
    """
    print(f"🔄 Calculating {calculation_type} zones for {instrument_name} using yfinance only...")
    
    # Direct yfinance implementation - avoid complex fallback logic
    try:
        import yfinance as yf
        
        # Use simple ticker mapping
        TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        
        if instrument_name not in TICKERS:
            print(f"❌ Instrument {instrument_name} not supported")
            return calculate_fallback_zones(instrument_name, calculation_type)
            
        ticker_symbol = TICKERS[instrument_name]
        
        # Use 6-month period that was working
        print(f"📊 Fetching yfinance data for {ticker_symbol}...")
        df_zones = yf.Ticker(ticker_symbol).history(period="6mo", interval="1d")
        
        if df_zones.empty:
            print(f"❌ No yfinance data returned for {ticker_symbol}")
            return calculate_fallback_zones(instrument_name, calculation_type)
        
        print(f"✅ yfinance data: {len(df_zones)} records from {df_zones.index[0]} to {df_zones.index[-1]}")
        
        # Convert index to datetime
        df_zones.index = pd.to_datetime(df_zones.index)
        
        # Resample to weekly data
        resample_period = 'W' if calculation_type == "Weekly" else 'ME'
        agg_df = df_zones.resample(resample_period).agg({
            'Open': 'first', 
            'High': 'max', 
            'Low': 'min'
        }).dropna()
        
        if len(agg_df) < 5:
            print(f"❌ Insufficient weekly data: {len(agg_df)} records")
            return calculate_fallback_zones(instrument_name, calculation_type)
        
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
        }).dropna()
        
        if latest_zones.empty:
            print(f"❌ No zone data calculated")
            return calculate_fallback_zones(instrument_name, calculation_type)
        
        latest = latest_zones.iloc[-1]
        
        # Calculate supply and demand zones
        supply_zone = round(max(latest['u1'], latest['u2']), 2)
        demand_zone = round(min(latest['l1'], latest['l2']), 2)
        
        print(f"✅ YFinance method successful for {instrument_name}")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ YFinance method failed for {instrument_name}: {e}")
        import traceback
        traceback.print_exc()
        return calculate_fallback_zones(instrument_name, calculation_type)

def calculate_zones_nifsel_exact(instrument_name, calculation_type):
    """
    EXACT implementation of NIFSEL.py zone calculation logic.
    This is a 1:1 replication of the NIFSEL.py algorithm.
    """
    try:
        import yfinance as yf
        
        # EXACT ticker mapping from NIFSEL.py
        TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        
        if instrument_name not in TICKERS:
            print(f"❌ Instrument {instrument_name} not supported in NIFSEL.py logic")
            return None, None
            
        ticker_symbol = TICKERS[instrument_name]
        print(f"📊 Fetching data for {ticker_symbol} using EXACT NIFSEL.py logic...")
        
        # EXACT period logic from NIFSEL.py
        if calculation_type == "Weekly" and instrument_name == "NIFTY":
            period = "6mo"  # EXACT from NIFSEL.py for Weekly NIFTY
        else:
            period = "5y"   # Default for other calculations
            
        # Fetch historical data
        df_zones = yf.Ticker(ticker_symbol).history(period=period, interval="1d")
        
        if df_zones.empty:
            print(f"❌ No data received from yfinance for {ticker_symbol}")
            return None, None
            
        print(f"✅ Retrieved {len(df_zones)} days of data for {ticker_symbol}")
        
        # Convert index to datetime (EXACT from NIFSEL.py)
        df_zones.index = pd.to_datetime(df_zones.index)
        
        # EXACT resampling logic from NIFSEL.py
        resample_period = 'W' if calculation_type == "Weekly" else 'ME'
        agg_df = df_zones.resample(resample_period).agg({
            'Open': 'first', 
            'High': 'max', 
            'Low': 'min'
        }).dropna()
        
        if len(agg_df) < 10:
            print(f"❌ Insufficient resampled data for {instrument_name} (need 10, got {len(agg_df)})")
            return None, None
            
        print(f"✅ Resampled to {len(agg_df)} periods for zone calculation")
        
        # EXACT rolling range calculation from NIFSEL.py
        rng5 = (agg_df['High'] - agg_df['Low']).rolling(5).mean()
        rng10 = (agg_df['High'] - agg_df['Low']).rolling(10).mean()
        
        # EXACT base price logic from NIFSEL.py
        base = agg_df['Open']
        
        # EXACT zone calculation from NIFSEL.py
        u1 = base + 0.5 * rng5  # Upper zone 1
        u2 = base + 0.5 * rng10  # Upper zone 2
        l1 = base - 0.5 * rng5   # Lower zone 1
        l2 = base - 0.5 * rng10  # Lower zone 2
        
        # Get the latest zones (EXACT from NIFSEL.py)
        latest_zones = pd.DataFrame({
            'u1': u1, 
            'u2': u2, 
            'l1': l1, 
            'l2': l2
        }).dropna().iloc[-1]
        
        # EXACT supply/demand calculation from NIFSEL.py
        supply_zone = round(max(latest_zones['u1'], latest_zones['u2']), 2)
        demand_zone = round(min(latest_zones['l1'], latest_zones['l2']), 2)
        
        print(f"✅ EXACT NIFSEL.py zones calculated for {instrument_name} ({calculation_type}):")
        print(f"   Latest Base (Open): ₹{base.iloc[-1]:.2f}")
        print(f"   RNG5 (5-period SMA): ₹{rng5.iloc[-1]:.2f}")
        print(f"   RNG10 (10-period SMA): ₹{rng10.iloc[-1]:.2f}")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        print(f"   Zone Range: ₹{supply_zone - demand_zone:.2f}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ NIFSEL.py exact method failed for {instrument_name}: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def try_yfinance_zones(instrument_name, calculation_type):
    """
    Enhanced zone calculation using yfinance with optimized single call
    """
    try:
        print(f"🔄 Calculating {calculation_type} zones for {instrument_name}...")
        
        # Skip DhanHQ for now due to API issues - use yfinance directly
        TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        
        if instrument_name not in TICKERS:
            return None, None
            
        ticker_symbol = TICKERS[instrument_name]
        
        # Use optimized period based on calculation type
        if calculation_type == "Weekly":
            period = "6mo"  # 6 months is sufficient for weekly zones
        elif calculation_type == "Monthly":
            period = "2y"   # 2 years for monthly zones
        else:
            period = "1y"   # 1 year default
            
        # Single yfinance call to avoid rate limiting
        df_zones = yf.Ticker(ticker_symbol).history(period=period, interval="1d")
            
        if df_zones.empty:
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
        
        print(f"✅ {calculation_type} zones calculated using yfinance for {instrument_name}:")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ yfinance method failed for {instrument_name}: {e}")
        return None, None


def calculate_zones_from_data(df, instrument_name, calculation_type, data_source):
    """
    Calculate supply/demand zones from historical data (DhanHQ format)
    """
    try:
        if len(df) < 10:
            print(f"❌ Insufficient data for {instrument_name}")
            return None, None
        
        # Determine period for zone calculation
        if calculation_type == 'Weekly':
            period = min(21, len(df))  # 3 weeks of data
        elif calculation_type == 'Monthly':
            period = min(63, len(df))  # 3 months of data
        else:
            period = min(126, len(df))  # 6 months of data
        
        recent_data = df.tail(period)
        
        # Calculate resistance (supply) and support (demand) levels
        highs = recent_data['High']
        lows = recent_data['Low']
        closes = recent_data['Close']
        
        # Advanced zone calculation
        resistance_levels = []
        support_levels = []
        
        # Find swing highs and lows
        for i in range(2, len(recent_data) - 2):
            current_high = highs.iloc[i]
            current_low = lows.iloc[i]
            
            # Check for swing high
            if (current_high > highs.iloc[i-1] and current_high > highs.iloc[i+1] and
                current_high > highs.iloc[i-2] and current_high > highs.iloc[i+2]):
                resistance_levels.append(current_high)
            
            # Check for swing low
            if (current_low < lows.iloc[i-1] and current_low < lows.iloc[i+1] and
                current_low < lows.iloc[i-2] and current_low < lows.iloc[i+2]):
                support_levels.append(current_low)
        
        current_price = closes.iloc[-1]
        
        # Find relevant zones
        supply_zone = None
        demand_zone = None
        
        # Supply zone: nearest resistance above current price
        valid_resistance = [r for r in resistance_levels if r > current_price]
        if valid_resistance:
            supply_zone = min(valid_resistance)
        else:
            # Use recent high if no resistance found
            supply_zone = highs.max()
        
        # Demand zone: nearest support below current price
        valid_support = [s for s in support_levels if s < current_price]
        if valid_support:
            demand_zone = max(valid_support)
        else:
            # Use recent low if no support found
            demand_zone = lows.min()
        
        # Round to nearest 50 for NIFTY, 100 for BANKNIFTY
        if 'NIFTY' in instrument_name.upper() and 'BANK' not in instrument_name.upper():
            supply_zone = round(supply_zone / 50) * 50
            demand_zone = round(demand_zone / 50) * 50
        else:
            supply_zone = round(supply_zone / 100) * 100
            demand_zone = round(demand_zone / 100) * 100
        
        print(f"✅ {calculation_type} zones calculated using {data_source} for {instrument_name}:")
        print(f"   Current Price: ₹{current_price}")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        print(f"   Zone Range: ₹{supply_zone - demand_zone}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ Error calculating zones from data: {e}")
        return None, None

def calculate_fallback_zones(instrument_name, calculation_type):
    """
    Calculate zones using mathematical model when live data is unavailable
    """
    try:
        # Get current price estimate from option chain or use market estimates
        current_price = get_current_market_price(instrument_name)
        
        if current_price is None:
            # Use realistic market estimates as of 2025
            current_price = 24800 if instrument_name == "NIFTY" else 51500
            
        # Calculate volatility-based zones
        if calculation_type == "Weekly":
            # Weekly volatility estimates for Indian markets
            volatility_percent = 0.015 if instrument_name == "NIFTY" else 0.018  # 1.5% for NIFTY, 1.8% for BANKNIFTY
        else:  # Monthly
            volatility_percent = 0.045 if instrument_name == "NIFTY" else 0.055  # 4.5% for NIFTY, 5.5% for BANKNIFTY
            
        # Calculate zones based on volatility
        volatility_points = current_price * volatility_percent
        
        # Supply zone (resistance) - above current price
        supply_zone = current_price + (volatility_points * 1.2)  # 20% buffer
        
        # Demand zone (support) - below current price  
        demand_zone = current_price - (volatility_points * 1.2)  # 20% buffer
        
        # Round to appropriate levels
        strike_increment = 50 if instrument_name == "NIFTY" else 100
        supply_zone = round(supply_zone / strike_increment) * strike_increment
        demand_zone = round(demand_zone / strike_increment) * strike_increment
        
        print(f"✅ {calculation_type} zones calculated using mathematical model for {instrument_name}:")
        print(f"   Current Price: ₹{current_price}")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        print(f"   Zone Range: ₹{supply_zone - demand_zone}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ Error in fallback zone calculation for {instrument_name}: {e}")
        return None, None

def get_current_market_price(instrument_name):
    """
    Get current market price using yfinance for chart analysis generation
    """
    try:
        # Use yfinance for chart analysis
        import yfinance as yf
        TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        
        if instrument_name in TICKERS:
            ticker_symbol = TICKERS[instrument_name]
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period='1d', interval='1m')
            
            if not data.empty:
                current_price = data['Close'].iloc[-1]
                print(f"✅ YFinance price for {instrument_name}: ₹{current_price}")
                return current_price
        
        # Fallback to option chain data if yfinance fails
        option_chain_data = get_option_chain_data(instrument_name)
        if option_chain_data:
            # Try DhanHQ structure first
            if 'data' in option_chain_data and 'last_price' in option_chain_data['data']:
                return float(option_chain_data['data']['last_price'])
            # Try NSE structure as fallback
            elif 'records' in option_chain_data:
                underlying_value = option_chain_data['records'].get('underlyingValue')
                if underlying_value:
                    return float(underlying_value)
    except:
        pass
    return None

def get_option_chain_data_for_trades(symbol, required_strikes):
    """
    Optimized function to fetch option chain data only for specific strikes
    Used for active trades to minimize API calls
    Uses local caching for better performance
    
    Args:
        symbol: NIFTY or BANKNIFTY
        required_strikes: List of strike prices that are needed for active trades
    
    Returns:
        Filtered option chain data containing only the required strikes
    """
    try:
        if not required_strikes:
            print(f"📝 No strikes required for {symbol}, skipping API call")
            return None
        
        # Try to load from cache first
        current_expiry = get_current_expiry(symbol)
        cached_data = load_option_chain_cache(symbol, current_expiry, max_age_minutes=3)
        
        if cached_data:
            print(f"� Using cached option chain data for {symbol}")
            return filter_strikes_from_data(cached_data, required_strikes)
            
        print(f"�📡 Fetching optimized option chain data for {symbol} - {len(required_strikes)} strikes: {required_strikes}")
        
        # Fetch fresh data (this is unavoidable for current prices)
        fresh_data = _fetch_fresh_option_chain_data(symbol)
        if not fresh_data:
            print(f"❌ Failed to fetch fresh data for {symbol}")
            return None
        
        # Save to cache for future use
        save_option_chain_cache(symbol, current_expiry, fresh_data)
        
        # Filter data to include only required strikes
        filtered_data = filter_strikes_from_data(fresh_data, required_strikes)
        
        return filtered_data
        
    except Exception as e:
        print(f"❌ Error in optimized option chain fetch for {symbol}: {e}")
        return None

def filter_strikes_from_data(data, required_strikes):
    """
    Filter option chain data to include only required strikes
    """
    try:
        filtered_data = data.copy()
        
        # Handle DhanHQ data structure
        if 'data' in data and 'oc' in data['data']:
            oc_data = data['data']['oc']
            filtered_oc = {}
            
            for strike_str, strike_data in oc_data.items():
                try:
                    strike_price = float(strike_str)
                    if strike_price in required_strikes:
                        filtered_oc[strike_str] = strike_data
                        print(f"✅ Included strike {strike_price}")
                except (ValueError, KeyError):
                    continue
            
            filtered_data['data']['oc'] = filtered_oc
            original_count = len(oc_data)
            filtered_count = len(filtered_oc)
            print(f"🎯 Optimized: {filtered_count}/{original_count} strikes (saved {original_count-filtered_count} strikes)")
            
        # Handle NSE data structure (fallback)
        elif 'records' in data and 'data' in data['records']:
            original_data = data['records']['data']
            filtered_records = []
            
            for item in original_data:
                strike_price = item.get('strikePrice')
                if strike_price in required_strikes:
                    filtered_records.append(item)
                    print(f"✅ Included strike {strike_price}")
            
            filtered_data['records']['data'] = filtered_records
            original_count = len(original_data)
            filtered_count = len(filtered_records)
            print(f"🎯 Optimized: {filtered_count}/{original_count} strikes (saved {original_count-filtered_count} strikes)")
        
        return filtered_data
        
    except Exception as e:
        print(f"❌ Error filtering strikes: {e}")
        return data

def get_current_expiry(symbol):
    """
    Get the current/nearest expiry for a symbol
    """
    try:
        expiry_dates = get_option_chain_expiry_dates_only(symbol)
        if expiry_dates and len(expiry_dates) > 0:
            return expiry_dates[0]  # Return first (nearest) expiry
        else:
            # Fallback to next Thursday
            from datetime import datetime, timedelta
            today = datetime.now().date()
            days_until_thursday = (3 - today.weekday()) % 7
            if days_until_thursday == 0:
                days_until_thursday = 7
            next_thursday = today + timedelta(days=days_until_thursday)
            return next_thursday.strftime("%d-%b-%Y")
    except Exception as e:
        print(f"❌ Error getting current expiry: {e}")
        return "28-Aug-2025"  # Fallback

def get_option_chain_data(symbol):
    """
    Get complete option chain data with prices for analysis
    Always fetches fresh data when analysis requires actual option prices
    """
    try:
        print(f"📡 Fetching fresh option chain data for analysis: {symbol}")
        debug_file = r"C:\Users\manir\Desktop\debug_log.txt"
        
        def debug_log(message):
            with open(debug_file, 'a', encoding='utf-8') as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                f.write(f"[{timestamp}] OPTION_CHAIN: {message}\n")
        
        debug_log(f"📡 get_option_chain_data called for {symbol} - fetching fresh data")
        
        # Always fetch fresh data for analysis to get current prices
        fresh_data = _fetch_fresh_option_chain_data(symbol)
        if fresh_data:
            # Update cache if we get expiry dates
            if 'expiryDates' in fresh_data:
                update_expiry_cache(symbol, fresh_data['expiryDates'])
            print(f"✅ Fresh option chain data fetched for {symbol}")
            debug_log(f"✅ Fresh option chain data fetched successfully")
            return fresh_data
        
        # If fresh data fails, try fallback
        print(f"⚠️ Fresh data failed, trying fallback for {symbol}")
        debug_log(f"⚠️ Fresh data failed, trying fallback")
        return get_fallback_expiry_data(symbol)
            
    except Exception as e:
        print(f"❌ Error in option chain fetch for {symbol}: {e}")
        debug_log(f"❌ Error in option chain fetch: {e}")
        return get_fallback_expiry_data(symbol)

def get_option_chain_expiry_dates_only(symbol):
    """
    Get only expiry dates using cached data when available (for UI dropdowns)
    This is the optimized version that uses cache for expiry dates only
    """
    try:
        # Check if we should refresh expiry cache (every Thursday)
        if should_refresh_expiry_cache():
            print(f"🔄 Thursday refresh: Updating expiry cache for {symbol}...")
            fresh_data = _fetch_fresh_option_chain_data(symbol)
            if fresh_data and 'expiryDates' in fresh_data:
                update_expiry_cache(symbol, fresh_data['expiryDates'])
                return fresh_data['expiryDates']
        
        # Try to get from cache first - this is the main optimization
        cached_expiry_dates = get_cached_expiry_dates(symbol)
        if cached_expiry_dates:
            print(f"✅ Using local cached expiry dates for {symbol}: {len(cached_expiry_dates)} dates (no API call needed)")
            return cached_expiry_dates
        
        # Only fetch fresh data if no cache exists
        print(f"🔄 No cache available, fetching fresh data for {symbol} (first time)...")
        fresh_data = _fetch_fresh_option_chain_data(symbol)
        if fresh_data and 'expiryDates' in fresh_data:
            update_expiry_cache(symbol, fresh_data['expiryDates'])
            return fresh_data['expiryDates']
        
        # If all else fails, use fallback
        fallback_data = get_fallback_expiry_data(symbol)
        return fallback_data.get('expiryDates', []) if fallback_data else []
            
    except Exception as e:
        print(f"❌ Error in expiry dates fetch for {symbol}: {e}")
        fallback_data = get_fallback_expiry_data(symbol)
        return fallback_data.get('expiryDates', []) if fallback_data else []

def _fetch_fresh_option_chain_data(symbol):
    """
    Internal function to fetch fresh option chain data using NSE API only
    """
    try:
        # Use NSE API only for option chain data
        print(f"🔄 Fetching NSE option chain for {symbol}...")
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        
        # Get a session cookie first
        session.get(f"https://www.nseindia.com/get-quotes/derivatives?symbol={symbol}", headers=headers, timeout=15)
        time.sleep(1)
        
        # Fetch option chain data
        response = session.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ NSE option chain for {symbol} fetched successfully")
        return data
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching NSE option chain for {symbol}: {e}")
        return None
    except Exception as e:
        print(f"❌ General error in NSE fetch for {symbol}: {e}")
        return None

def get_fallback_expiry_data(symbol):
    """
    Generate simple fallback expiry dates when NSE fails
    """
    try:
        from datetime import datetime, timedelta
        
        # Generate next 4 weekly expiries (Thursdays)
        today = datetime.now().date()
        days_until_thursday = (3 - today.weekday()) % 7  # Thursday is weekday 3
        if days_until_thursday == 0:  # If today is Thursday, get next Thursday
            days_until_thursday = 7
            
        next_thursday = today + timedelta(days=days_until_thursday)
        
        expiries = []
        for i in range(4):  # Next 4 weekly expiries
            expiry_date = next_thursday + timedelta(weeks=i)
            expiries.append(expiry_date.strftime("%d-%b-%Y"))
        
        print(f"🔄 Using fallback expiry dates for {symbol}: {expiries}")
        
        # Return in consistent format
        return {
            'expiryDates': expiries,
            'symbol': symbol,
            'source': 'fallback',
            'timestamp': datetime.now().isoformat(),
            'records': {
                'expiryDates': expiries,
                'data': [],
                'underlyingValue': get_current_market_price(symbol) or 24500
            }
        }
        
    except Exception as e:
        print(f"❌ Fallback expiry generation error: {e}")
        # Ultimate fallback with static dates
        return {
            'expiryDates': [
                (datetime.now() + timedelta(days=7)).strftime("%d-%b-%Y"),
                (datetime.now() + timedelta(days=14)).strftime("%d-%b-%Y"),
                (datetime.now() + timedelta(days=21)).strftime("%d-%b-%Y"),
                (datetime.now() + timedelta(days=28)).strftime("%d-%b-%Y")
            ],
            'symbol': symbol,
            'source': 'ultimate_fallback'
        }

# --- Local Data Caching Functions ---

def save_option_chain_cache(symbol, expiry, data):
    """
    Save option chain data to local cache for faster access
    """
    try:
        cache_key = f"{symbol}_{expiry}"
        cache_data = {}
        
        # Load existing cache
        if os.path.exists(OPTION_CHAIN_CACHE_FILE):
            with open(OPTION_CHAIN_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
        
        # Add new data with timestamp
        cache_data[cache_key] = {
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'expiry': expiry
        }
        
        # Save back to file
        with open(OPTION_CHAIN_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"💾 Saved option chain cache for {symbol} {expiry}")
        
    except Exception as e:
        print(f"❌ Error saving option chain cache: {e}")

def load_option_chain_cache(symbol, expiry, max_age_minutes=5):
    """
    Load option chain data from local cache if it's fresh enough
    """
    try:
        cache_key = f"{symbol}_{expiry}"
        
        if not os.path.exists(OPTION_CHAIN_CACHE_FILE):
            return None
        
        with open(OPTION_CHAIN_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        
        if cache_key not in cache_data:
            return None
        
        cached_item = cache_data[cache_key]
        cache_time = datetime.fromisoformat(cached_item['timestamp'])
        age_minutes = (datetime.now() - cache_time).total_seconds() / 60
        
        if age_minutes <= max_age_minutes:
            print(f"📋 Using cached option chain data for {symbol} {expiry} (age: {age_minutes:.1f}min)")
            return cached_item['data']
        else:
            print(f"⏰ Cache too old for {symbol} {expiry} (age: {age_minutes:.1f}min)")
            return None
            
    except Exception as e:
        print(f"❌ Error loading option chain cache: {e}")
        return None

def save_trades_data_cache(trades_data):
    """
    Save trades data to local cache for faster access
    """
    try:
        cache_data = {
            'trades': trades_data,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(TRADES_DATA_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"💾 Saved trades data cache with {len(trades_data)} trades")
        
    except Exception as e:
        print(f"❌ Error saving trades data cache: {e}")

def load_trades_data_cache(max_age_minutes=2):
    """
    Load trades data from local cache if it's fresh enough
    """
    try:
        if not os.path.exists(TRADES_DATA_CACHE_FILE):
            return None
        
        with open(TRADES_DATA_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        age_minutes = (datetime.now() - cache_time).total_seconds() / 60
        
        if age_minutes <= max_age_minutes:
            print(f"📋 Using cached trades data (age: {age_minutes:.1f}min)")
            return cache_data['trades']
        else:
            print(f"⏰ Trades cache too old (age: {age_minutes:.1f}min)")
            return None
            
    except Exception as e:
        print(f"❌ Error loading trades data cache: {e}")
        return None

def get_active_trades_strikes():
    """
    Get only the strikes that are currently needed for active trades
    Returns dict with 'NIFTY': [strikes], 'BANKNIFTY': [strikes]
    """
    try:
        trades = load_trades()
        active_trades = [t for t in trades if t.get('status') == 'Running']
        
        strikes_needed = {'NIFTY': set(), 'BANKNIFTY': set()}
        
        for trade in active_trades:
            instrument = trade.get('instrument')
            if instrument in ['NIFTY', 'BANKNIFTY']:
                ce_strike = trade.get('ce_strike')
                pe_strike = trade.get('pe_strike')
                
                if ce_strike:
                    strikes_needed[instrument].add(float(ce_strike))
                if pe_strike:
                    strikes_needed[instrument].add(float(pe_strike))
        
        # Convert sets to sorted lists
        result = {}
        for instrument, strikes in strikes_needed.items():
            result[instrument] = sorted(list(strikes))
        
        print(f"🎯 Active trades need: NIFTY {len(result['NIFTY'])} strikes, BANKNIFTY {len(result['BANKNIFTY'])} strikes")
        return result
        
    except Exception as e:
        print(f"❌ Error getting active trades strikes: {e}")
        return {'NIFTY': [], 'BANKNIFTY': []}

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

def send_telegram_message_with_credentials(message, bot_token, chat_id):
    """Send a test message using provided credentials (for testing purposes)."""
    if not bot_token or not chat_id:
        return False
        
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, data={
            'chat_id': chat_id, 
            'text': message, 
            'parse_mode': 'Markdown'
        })
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send test message to Telegram: {e}")
        return False

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
    """
    Generate chart analysis using yfinance data only for reliable historical data
    """
    # Create a debug log file
    debug_file = r"C:\Users\manir\Desktop\debug_log.txt"
    
    def debug_log(message):
        with open(debug_file, 'a', encoding='utf-8') as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            f.write(f"[{timestamp}] UTILS: {message}\n")
        print(f"UTILS: {message}")  # Also print to console
    
    debug_log(f"=== generate_analysis() called ===")
    debug_log(f"Parameters: instrument={instrument_name}, calc_type={calculation_type}, expiry={selected_expiry_str}")
    debug_log("📊 Using yfinance for chart analysis generation")
    
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    if not all([instrument_name, calculation_type, selected_expiry_str]):
        debug_log("❌ Missing required parameters")
        return None, "Please select valid inputs."

    ticker_symbol = TICKERS[instrument_name]
    debug_log(f"Using ticker symbol: {ticker_symbol}")
    
    lot_size = get_lot_size(instrument_name)
    strike_increment = 50 if instrument_name == "NIFTY" else 100
    
    # Calculate weekly supply/demand zones using yfinance only
    debug_log(f"📊 Calculating {calculation_type} supply/demand zones using yfinance...")
    supply_zone, demand_zone = calculate_weekly_zones(instrument_name, calculation_type)
    
    if supply_zone is None or demand_zone is None:
        debug_log("❌ Failed to calculate zones, using fallback method")
        # Fallback to simple price-based method
        supply_zone = None
        demand_zone = None
    else:
        debug_log(f"✅ Zones calculated - Supply: ₹{supply_zone}, Demand: ₹{demand_zone}")
    
    zone_label = calculation_type
    
    # Single option chain fetch - on-demand only when analysis is requested
    print("📡 Fetching option chain data (on-demand)...")
    try:
        option_chain_data = get_option_chain_data(instrument_name)
        if option_chain_data:
            print("✅ Option chain data fetched successfully")
            debug_log("✅ Option chain fetch successful")
        else:
            print("❌ Option chain data is None")
    except Exception as e:
        print(f"❌ Exception fetching option chain: {e}")
        return None, f"Error fetching option chain: {e}"
    
    if not option_chain_data:
        print("❌ No option chain data available - using yfinance for current price and sample option data")
        # Use yfinance for current price when option chain fails
        current_price = get_current_market_price(instrument_name) or (24750 if instrument_name == "NIFTY" else 51500)
        ce_prices = {24800: 45.5, 24850: 35.2, 24900: 26.8}
        pe_prices = {24700: 42.3, 24650: 33.1, 24600: 25.7}
        debug_log(f"🔄 Using yfinance current price {current_price} and sample option data due to API unavailability")
    else:
        try:
            # Try different possible structures for underlying value
            if 'records' in option_chain_data and 'underlyingValue' in option_chain_data['records']:
                current_price = option_chain_data['records']['underlyingValue']
            elif 'underlyingValue' in option_chain_data:
                current_price = option_chain_data['underlyingValue']
            elif 'underlying' in option_chain_data:
                current_price = option_chain_data['underlying']
            else:
                # Fallback to yfinance current market price for chart analysis
                current_price = get_current_market_price(instrument_name) or (24750 if instrument_name == "NIFTY" else 51500)
                debug_log(f"⚠️ Could not find underlying value in option chain data, using yfinance fallback: {current_price}")
        except Exception as e:
            debug_log(f"❌ Error reading underlying value: {e}")
            current_price = get_current_market_price(instrument_name) or (24750 if instrument_name == "NIFTY" else 51500)
            debug_log(f"🔄 Using yfinance fallback current price: {current_price}")
    expiry_label = datetime.strptime(selected_expiry_str, '%d-%b-%Y').strftime("%d-%b")
    
    if option_chain_data:
        # Extract option data from NSE API structure
        ce_prices, pe_prices = {}, {}
        
        # Get current price from the chain data  
        if 'records' in option_chain_data and 'underlyingValue' in option_chain_data['records']:
            current_price = option_chain_data['records']['underlyingValue']
            debug_log(f"📊 Updated current price from NSE option chain: {current_price}")
        
        # Debug: Log the actual option chain data structure
        debug_log(f"📊 NSE option chain data keys: {list(option_chain_data.keys()) if isinstance(option_chain_data, dict) else 'Not a dict'}")
        if isinstance(option_chain_data, dict) and 'records' in option_chain_data:
            debug_log(f"📊 NSE records keys: {list(option_chain_data['records'].keys()) if isinstance(option_chain_data['records'], dict) else 'Not a dict'}")
        
        # Extract option data from NSE structure
        if 'records' in option_chain_data and 'data' in option_chain_data['records']:
            for item in option_chain_data['records']['data']:
                if item.get("expiryDate") == selected_expiry_str:
                    if item.get("CE"): 
                        ce_prices[item['strikePrice']] = item["CE"]["lastPrice"]
                    if item.get("PE"): 
                        pe_prices[item['strikePrice']] = item["PE"]["lastPrice"]
            debug_log(f"📊 NSE API data - CE: {len(ce_prices)}, PE: {len(pe_prices)} strikes")
        else:
            debug_log("📊 NSE structure not found in option chain data")
            debug_log(f"📊 Available option chain data structure: {str(option_chain_data)[:500]}...")
    
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
    
    # Calculate target and stoploss with global round-off by 50 (reverted to working coefficient 0.80)
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
    fig.suptitle(f'{instrument_name} {selected_expiry_str}', 
                fontsize=18, fontweight='bold', y=0.94, color='#1e293b', ha='center')
    
    # Enhanced info box with global theme styling (removed ₹ symbol)
    info_text = f"{instrument_name}: {int(current_price)}\nExpiry: {expiry_label}\nGenerated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}"
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
    
    
    # SEBI disclaimer with global theme
    ax.text(0.5, 0.08, "We are not SEBI registered. For educational purposes only.", 
            transform=ax.transAxes, ha='center', va='center',
            fontsize=9, color='#dc2626', style='italic', fontweight='600')
    
    # Enhanced FiFTO branding with copyright and red "O" (no space)
    ax.text(0.46, 0.02, "© FiFT", transform=ax.transAxes, ha='center', va='center',
            fontsize=11, color='#16a34a', fontweight='bold', alpha=0.9)
    ax.text(0.495, 0.02, "O", transform=ax.transAxes, ha='center', va='center',
            fontsize=11, color='#dc2626', fontweight='bold', alpha=0.9)  # Red "O"
    ax.text(0.52, 0.02, " Analytics", transform=ax.transAxes, ha='left', va='center',
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
    start_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    day_name = datetime.now().strftime("%A")
    entry_tag = f"{day_name} Selling"
    
    # Add timestamp to make trade IDs more unique
    timestamp_suffix = datetime.now().strftime("%I%M%p")
    
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
            
        # Create trade object
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
            "stoploss_amount": entry.get('Stoploss', 0)
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
    start_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
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