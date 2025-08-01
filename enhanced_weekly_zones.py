# Enhanced Weekly Zone Calculation Implementation
# This is a proposed enhancement to the existing utils.py

import yfinance as yf
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta

# These functions would be imported from utils.py in the actual implementation
def get_option_chain_data(symbol):
    """Placeholder - would import from utils.py"""
    pass

def get_lot_size(instrument):
    """Placeholder - would import from utils.py"""
    return 75 if instrument == "NIFTY" else 35

def round_to_nearest_50(value):
    """Placeholder - would import from utils.py"""
    return round(value / 50) * 50

def calculate_weekly_zones(instrument_name):
    """
    Calculate weekly support/resistance zones using technical analysis
    """
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    ticker_symbol = TICKERS.get(instrument_name)
    
    if not ticker_symbol:
        return None
    
    try:
        # Fetch 1 month of daily data for weekly analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        ticker = yf.Ticker(ticker_symbol)
        hist_data = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if hist_data.empty:
            return None
            
        # Calculate weekly aggregation (last 5 trading days)
        weekly_data = hist_data.tail(5)  # Last week
        
        weekly_high = weekly_data['High'].max()
        weekly_low = weekly_data['Low'].min()
        weekly_close = weekly_data['Close'].iloc[-1]
        weekly_open = weekly_data['Open'].iloc[0]
        
        # Calculate Pivot Points (Traditional Method)
        pivot = (weekly_high + weekly_low + weekly_close) / 3
        
        # Resistance Levels
        r1 = (2 * pivot) - weekly_low
        r2 = pivot + (weekly_high - weekly_low)
        r3 = weekly_high + 2 * (pivot - weekly_low)
        
        # Support Levels
        s1 = (2 * pivot) - weekly_high
        s2 = pivot - (weekly_high - weekly_low)
        s3 = weekly_low - 2 * (weekly_high - pivot)
        
        # Calculate additional zones
        mid_point = (weekly_high + weekly_low) / 2
        
        # Volume-weighted average price (VWAP) for the week
        if 'Volume' in weekly_data.columns:
            vwap = (weekly_data['Close'] * weekly_data['Volume']).sum() / weekly_data['Volume'].sum()
        else:
            vwap = weekly_close
            
        zones = {
            'current_price': weekly_close,
            'weekly_high': weekly_high,
            'weekly_low': weekly_low,
            'weekly_open': weekly_open,
            'pivot': pivot,
            'resistance_1': r1,
            'resistance_2': r2,
            'resistance_3': r3,
            'support_1': s1,
            'support_2': s2,
            'support_3': s3,
            'mid_point': mid_point,
            'vwap': vwap,
            'week_range': weekly_high - weekly_low,
            'trend': 'bullish' if weekly_close > weekly_open else 'bearish'
        }
        
        return zones
        
    except Exception as e:
        print(f"Error calculating weekly zones: {e}")
        return None

def select_strikes_from_zones(zones, instrument_name, calculation_type):
    """
    Enhanced strike selection based on weekly zones
    """
    if not zones:
        return None, None, None
        
    current_price = zones['current_price']
    strike_increment = 50 if instrument_name == "NIFTY" else 100
    
    # Zone-based strike selection
    if calculation_type == "Weekly":
        # Use weekly pivot levels for strike selection
        
        # CE Strikes: Around resistance levels
        if zones['trend'] == 'bullish':
            # In bullish trend, sell CEs at resistance levels
            ce_target = zones['resistance_1']
        else:
            # In bearish trend, sell CEs closer to current price
            ce_target = current_price + (zones['week_range'] * 0.3)
            
        # PE Strikes: Around support levels  
        if zones['trend'] == 'bearish':
            # In bearish trend, sell PEs at support levels
            pe_target = zones['support_1']
        else:
            # In bullish trend, sell PEs closer to current price
            pe_target = current_price - (zones['week_range'] * 0.3)
            
    else:  # Monthly
        # Use wider zones for monthly
        ce_target = zones['resistance_2']
        pe_target = zones['support_2']
    
    # Round to nearest strike increments
    ce_base = round(ce_target / strike_increment) * strike_increment
    pe_base = round(pe_target / strike_increment) * strike_increment
    
    # Create strike arrays
    strikes_ce = [
        ce_base,
        ce_base + strike_increment,
        ce_base + (2 * strike_increment)
    ]
    
    strikes_pe = [
        pe_base,
        pe_base - strike_increment,
        pe_base - (2 * strike_increment)
    ]
    
    # Ensure strikes are reasonable (not too far from current price)
    max_distance = zones['week_range'] * 1.5
    
    # Filter CE strikes
    strikes_ce = [s for s in strikes_ce if abs(s - current_price) <= max_distance and s > current_price]
    if len(strikes_ce) < 3:
        # Fallback to simple method if zone-based selection fails
        ce_high = math.ceil(current_price / strike_increment) * strike_increment
        strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
    
    # Filter PE strikes  
    strikes_pe = [s for s in strikes_pe if abs(s - current_price) <= max_distance and s < current_price]
    if len(strikes_pe) < 3:
        # Fallback to simple method if zone-based selection fails
        pe_high = math.floor(current_price / strike_increment) * strike_increment
        strikes_pe = [pe_high, pe_high - strike_increment, pe_high - (2 * strike_increment)]
    
    return strikes_ce[:3], strikes_pe[:3], zones

def enhanced_generate_analysis(instrument_name, calculation_type, selected_expiry_str):
    """
    Enhanced analysis with weekly zone calculations
    This replaces the existing generate_analysis function
    """
    debug_file = r"C:\Users\manir\Desktop\debug_log.txt"
    
    def debug_log(message):
        with open(debug_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] ENHANCED: {message}\n")
        print(f"ENHANCED: {message}")
    
    debug_log(f"=== Enhanced analysis with weekly zones ===")
    debug_log(f"Parameters: instrument={instrument_name}, calc_type={calculation_type}, expiry={selected_expiry_str}")
    
    # Calculate weekly zones first
    zones = calculate_weekly_zones(instrument_name)
    if zones:
        debug_log(f"📊 Weekly zones calculated:")
        debug_log(f"   Current: ₹{zones['current_price']:.2f}")
        debug_log(f"   Weekly High: ₹{zones['weekly_high']:.2f}")
        debug_log(f"   Weekly Low: ₹{zones['weekly_low']:.2f}")
        debug_log(f"   Pivot: ₹{zones['pivot']:.2f}")
        debug_log(f"   R1: ₹{zones['resistance_1']:.2f}, S1: ₹{zones['support_1']:.2f}")
        debug_log(f"   Trend: {zones['trend']}")
    else:
        debug_log("❌ Failed to calculate weekly zones, using fallback method")
        
    # Get option chain data
    option_chain_data = get_option_chain_data(instrument_name)
    if not option_chain_data:
        debug_log("❌ No option chain data available")
        return None, "Unable to fetch market data"
    
    current_price = option_chain_data['records']['underlyingValue']
    lot_size = get_lot_size(instrument_name)
    
    # Extract option prices
    ce_prices, pe_prices = {}, {}
    for item in option_chain_data['records']['data']:
        if item.get("expiryDate") == selected_expiry_str:
            if item.get("CE"): 
                ce_prices[item['strikePrice']] = item["CE"]["lastPrice"]
            if item.get("PE"): 
                pe_prices[item['strikePrice']] = item["PE"]["lastPrice"]
    
    # Enhanced strike selection using zones
    if zones:
        strikes_ce, strikes_pe, zone_info = select_strikes_from_zones(zones, instrument_name, calculation_type)
        debug_log(f"📊 Zone-based strikes:")
        debug_log(f"   CE: {strikes_ce}")
        debug_log(f"   PE: {strikes_pe}")
    else:
        # Fallback to original method
        strike_increment = 50 if instrument_name == "NIFTY" else 100
        ce_high = math.ceil(current_price / strike_increment) * strike_increment
        strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
        pe_high = math.floor(current_price / strike_increment) * strike_increment
        strikes_pe = [pe_high, pe_high - strike_increment, pe_high - (2 * strike_increment)]
        zone_info = None
        debug_log("📊 Using fallback strike selection")
    
    # Create DataFrame with enhanced data
    df = pd.DataFrame({
        "Entry": ["High Reward", "Mid Reward", "Low Reward"], 
        "CE Strike": strikes_ce, 
        "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce], 
        "PE Strike": strikes_pe, 
        "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe]
    })
    
    df["Combined Premium"] = df["CE Price"] + df["PE Price"]
    df["Target"] = df["Combined Premium"].apply(lambda x: round_to_nearest_50((x * 0.80 * lot_size)))
    df["Stoploss"] = df["Combined Premium"].apply(lambda x: round_to_nearest_50((x * 0.80 * lot_size)))
    
    # Add zone information to result
    analysis_data = {
        "instrument": instrument_name, 
        "expiry": selected_expiry_str, 
        "lot_size": lot_size, 
        "df_data": df.to_dict('records'),
        "zones": zones,  # Add zone data
        "zone_based": zones is not None,
        "calculation_type": calculation_type
    }
    
    debug_log(f"✅ Enhanced analysis completed with {'zone-based' if zones else 'fallback'} method")
    
    return analysis_data, f"Enhanced {calculation_type} analysis completed with weekly zones"

# Usage example:
if __name__ == "__main__":
    # Test the enhanced weekly zone calculation
    print("Testing Enhanced Weekly Zone Calculation...")
    
    for instrument in ["NIFTY", "BANKNIFTY"]:
        print(f"\n=== {instrument} ===")
        zones = calculate_weekly_zones(instrument)
        if zones:
            print(f"Current Price: ₹{zones['current_price']:.2f}")
            print(f"Weekly Range: ₹{zones['weekly_low']:.2f} - ₹{zones['weekly_high']:.2f}")
            print(f"Pivot: ₹{zones['pivot']:.2f}")
            print(f"Resistance: R1=₹{zones['resistance_1']:.2f}, R2=₹{zones['resistance_2']:.2f}")
            print(f"Support: S1=₹{zones['support_1']:.2f}, S2=₹{zones['support_2']:.2f}")
            print(f"Trend: {zones['trend']}")
        else:
            print("Failed to calculate zones")
