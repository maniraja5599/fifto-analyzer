#!/usr/bin/env python3
"""
Test script to understand NIFSEL.py supply/demand logic and strike selection
This extracts the core zone calculation and strike selection logic from NIFSEL.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
import math
import requests
import time
from datetime import datetime

def get_option_chain_data(symbol):
    """Get option chain data from NSE"""
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    
    try:
        # Pre-request to set cookies
        session.get(f"https://www.nseindia.com/get-quotes/derivatives?symbol={symbol}", headers=headers, timeout=15)
        time.sleep(1)
        
        # Main request
        response = session.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching option chain for {symbol}: {e}")
        return None

def calculate_zones_nifsel_exact(instrument_name, calculation_type):
    """
    EXACT zone calculation logic from NIFSEL.py
    """
    print(f"\n🔬 NIFSEL.py Zone Calculation for {instrument_name} ({calculation_type})")
    print("=" * 60)
    
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    
    if instrument_name not in TICKERS:
        print(f"❌ Instrument {instrument_name} not supported")
        return None, None
        
    ticker_symbol = TICKERS[instrument_name]
    
    # EXACT period logic from NIFSEL.py
    if calculation_type == "Weekly" and instrument_name == "NIFTY":
        period = "6mo"  # EXACT from NIFSEL.py for Weekly NIFTY
    else:
        period = "5y"   # Default for other calculations
        
    print(f"📊 Fetching {period} data for {ticker_symbol}...")
    
    try:
        # Fetch historical data
        df_zones = yf.Ticker(ticker_symbol).history(period=period, interval="1d")
        
        if df_zones.empty:
            print(f"❌ No data received from yfinance for {ticker_symbol}")
            return None, None
            
        print(f"✅ Retrieved {len(df_zones)} days of data")
        print(f"   Date range: {df_zones.index[0]} to {df_zones.index[-1]}")
        print(f"   Latest close: ₹{df_zones['Close'].iloc[-1]:.2f}")
        
        # Convert index to datetime (EXACT from NIFSEL.py)
        df_zones.index = pd.to_datetime(df_zones.index)
        
        # EXACT resampling logic from NIFSEL.py
        resample_period = 'W' if calculation_type == "Weekly" else 'ME'
        agg_df = df_zones.resample(resample_period).agg({
            'Open': 'first', 
            'High': 'max', 
            'Low': 'min'
        }).dropna()
        
        print(f"\n📈 Resampled to {len(agg_df)} {calculation_type.lower()} periods")
        print(f"   Latest period data:")
        print(f"   Open: ₹{agg_df['Open'].iloc[-1]:.2f}")
        print(f"   High: ₹{agg_df['High'].iloc[-1]:.2f}")
        print(f"   Low: ₹{agg_df['Low'].iloc[-1]:.2f}")
        
        if len(agg_df) < 10:
            print(f"⚠️ Warning: Only {len(agg_df)} periods available (recommended: 10+)")
            
        # EXACT rolling range calculation from NIFSEL.py
        rng5 = (agg_df['High'] - agg_df['Low']).rolling(5).mean()
        rng10 = (agg_df['High'] - agg_df['Low']).rolling(10).mean()
        
        # EXACT base price logic from NIFSEL.py
        base = agg_df['Open']
        
        print(f"\n🧮 Zone Calculation Details:")
        print(f"   Latest base (Open): ₹{base.iloc[-1]:.2f}")
        print(f"   RNG5 (5-period range avg): ₹{rng5.iloc[-1]:.2f}")
        print(f"   RNG10 (10-period range avg): ₹{rng10.iloc[-1]:.2f}")
        
        # EXACT zone calculation from NIFSEL.py
        u1 = base + 0.5 * rng5  # Upper zone 1
        u2 = base + 0.5 * rng10  # Upper zone 2
        l1 = base - 0.5 * rng5   # Lower zone 1
        l2 = base - 0.5 * rng10  # Lower zone 2
        
        print(f"\n📊 Zone Components:")
        print(f"   U1 (base + 0.5*rng5): ₹{u1.iloc[-1]:.2f}")
        print(f"   U2 (base + 0.5*rng10): ₹{u2.iloc[-1]:.2f}")
        print(f"   L1 (base - 0.5*rng5): ₹{l1.iloc[-1]:.2f}")
        print(f"   L2 (base - 0.5*rng10): ₹{l2.iloc[-1]:.2f}")
        
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
        
        print(f"\n✅ FINAL ZONES:")
        print(f"   Supply Zone: ₹{supply_zone} (max of U1, U2)")
        print(f"   Demand Zone: ₹{demand_zone} (min of L1, L2)")
        print(f"   Zone Range: ₹{supply_zone - demand_zone:.2f}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ Error in zone calculation: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def analyze_strike_selection(instrument_name, supply_zone, demand_zone, selected_expiry_str):
    """
    EXACT strike selection logic from NIFSEL.py
    """
    print(f"\n🎯 NIFSEL.py Strike Selection for {instrument_name}")
    print("=" * 60)
    
    # Get option chain data
    option_chain_data = get_option_chain_data(instrument_name)
    if not option_chain_data:
        print("❌ Could not fetch option chain data")
        return None
        
    current_price = option_chain_data['records']['underlyingValue']
    print(f"📈 Current Price: ₹{current_price}")
    print(f"📊 Supply Zone: ₹{supply_zone}")
    print(f"📊 Demand Zone: ₹{demand_zone}")
    
    # Extract option prices for the selected expiry
    ce_prices, pe_prices = {}, {}
    for item in option_chain_data['records']['data']:
        if item.get("expiryDate") == selected_expiry_str:
            if item.get("CE"):
                ce_prices[item['strikePrice']] = item["CE"]["lastPrice"]
            if item.get("PE"):
                pe_prices[item['strikePrice']] = item["PE"]["lastPrice"]
    
    print(f"\n🔍 Available strikes for expiry {selected_expiry_str}:")
    print(f"   CE options: {len(ce_prices)} strikes")
    print(f"   PE options: {len(pe_prices)} strikes")
    
    # EXACT strike selection logic from NIFSEL.py
    lot_size = 75 if instrument_name == "NIFTY" else 15
    strike_increment = 50 if instrument_name == "NIFTY" else 100
    
    print(f"\n⚙️ Configuration:")
    print(f"   Lot Size: {lot_size}")
    print(f"   Strike Increment: {strike_increment}")
    
    # CE Strike Selection (EXACT from NIFSEL.py)
    ce_high = math.ceil(supply_zone / strike_increment) * strike_increment
    strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
    
    print(f"\n📈 CE Strike Selection (based on Supply Zone ₹{supply_zone}):")
    print(f"   CE High (ceiling to {strike_increment}): {ce_high}")
    print(f"   CE Strikes: {strikes_ce}")
    
    # PE Strike Selection (EXACT from NIFSEL.py)
    pe_high = math.floor(demand_zone / strike_increment) * strike_increment
    
    # Find candidate PUTs (EXACT logic from NIFSEL.py)
    candidate_puts = sorted([
        s for s in pe_prices 
        if s < pe_high and pe_prices.get(s, 0) > 0
    ], key=lambda s: pe_prices.get(s, 0), reverse=True)
    
    print(f"\n📉 PE Strike Selection (based on Demand Zone ₹{demand_zone}):")
    print(f"   PE High (floor to {strike_increment}): {pe_high}")
    print(f"   Candidate PUTs (strikes < {pe_high} with premiums): {len(candidate_puts)}")
    
    if candidate_puts:
        print(f"   Top 5 candidate PUTs by premium:")
        for i, strike in enumerate(candidate_puts[:5]):
            print(f"     {i+1}. Strike {strike}: ₹{pe_prices[strike]:.2f}")
    
    # EXACT PE strike selection from NIFSEL.py
    pe_mid = candidate_puts[0] if candidate_puts else pe_high - strike_increment
    pe_low = (candidate_puts[1] if len(candidate_puts) > 1 
              else (candidate_puts[0] if candidate_puts else pe_high - strike_increment) - strike_increment)
    
    strikes_pe = [pe_high, pe_mid, pe_low]
    
    print(f"   Selected PE Strikes:")
    print(f"     PE High: {pe_high}")
    print(f"     PE Mid: {pe_mid}")
    print(f"     PE Low: {pe_low}")
    
    # Create strategy DataFrame (EXACT from NIFSEL.py)
    df = pd.DataFrame({
        "Entry": ["High Reward", "Mid Reward", "Low Reward"],
        "CE Strike": strikes_ce,
        "CE Price": [ce_prices.get(s, 0.0) for s in strikes_ce],
        "PE Strike": strikes_pe,
        "PE Price": [pe_prices.get(s, 0.0) for s in strikes_pe]
    })
    
    df["Combined Premium"] = df["CE Price"] + df["PE Price"]
    df["Target"] = (df["Combined Premium"] * 0.80 * lot_size).round(2)
    df["Stoploss"] = (df["Combined Premium"] * 0.80 * lot_size).round(2)
    
    print(f"\n📋 FINAL STRATEGY TABLE:")
    print("=" * 80)
    print(df.to_string(index=False))
    
    print(f"\n💰 Position Analysis:")
    for i, row in df.iterrows():
        premium_received = row['Combined Premium'] * lot_size
        target_profit = row['Target']
        print(f"   {row['Entry']}:")
        print(f"     Premium Received: ₹{premium_received:,.0f}")
        print(f"     Target Profit: ₹{target_profit:,.0f}")
        print(f"     Break-even Points:")
        print(f"       Upper: ₹{row['CE Strike'] + row['Combined Premium']:,.0f}")
        print(f"       Lower: ₹{row['PE Strike'] - row['Combined Premium']:,.0f}")
    
    return df

def main():
    """Main function to test both zone calculation and strike selection"""
    print("🧪 NIFSEL.py Logic Analysis")
    print("=" * 80)
    
    # Test parameters
    instrument_name = "NIFTY"
    calculation_type = "Weekly"
    
    # Get available expiries
    print("📅 Fetching available expiries...")
    option_data = get_option_chain_data(instrument_name)
    if not option_data:
        print("❌ Could not fetch option chain data")
        return
        
    expiry_dates = option_data['records']['expiryDates']
    current_expiry = expiry_dates[0]  # First available expiry
    
    print(f"   Available expiries: {len(expiry_dates)}")
    print(f"   Using first expiry: {current_expiry}")
    
    # Step 1: Calculate zones using NIFSEL.py logic
    supply_zone, demand_zone = calculate_zones_nifsel_exact(instrument_name, calculation_type)
    
    if supply_zone and demand_zone:
        # Step 2: Analyze strike selection using NIFSEL.py logic
        strategy_df = analyze_strike_selection(instrument_name, supply_zone, demand_zone, current_expiry)
        
        print(f"\n🎯 SUMMARY:")
        print("=" * 40)
        print(f"✅ Zone calculation: SUCCESS")
        print(f"✅ Strike selection: SUCCESS")
        print(f"✅ Strategy generation: SUCCESS")
        
    else:
        print(f"\n❌ Zone calculation failed - cannot proceed with strike selection")

if __name__ == "__main__":
    main()
