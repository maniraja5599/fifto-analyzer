#!/usr/bin/env python3
"""
Test both NIFSEL.py logic and current utils.py zone calculation
Compare the different approaches to understand the differences
"""

import yfinance as yf
import pandas as pd
import numpy as np
import math
import sys
import os
from datetime import datetime

# Add the analyzer module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'analyzer'))

def test_yfinance_data_availability():
    """Test if yfinance is working for NIFTY symbols"""
    print("🔍 Testing YFinance Data Availability")
    print("=" * 50)
    
    symbols = ["^NSEI", "NIFTY.NS", "^NSEBANK", "BANKNIFTY.NS"]
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}:")
        try:
            ticker = yf.Ticker(symbol)
            
            # Test different periods
            periods = ["1mo", "3mo", "6mo", "1y", "5y"]
            
            for period in periods:
                try:
                    data = ticker.history(period=period, interval="1d")
                    if not data.empty:
                        print(f"   ✅ {period}: {len(data)} records (Latest: ₹{data['Close'].iloc[-1]:.2f})")
                        # Show first successful period details
                        if period == "1mo":
                            print(f"      Date range: {data.index[0]} to {data.index[-1]}")
                        break
                    else:
                        print(f"   ❌ {period}: No data")
                except Exception as e:
                    print(f"   ❌ {period}: Error - {e}")
            else:
                print(f"   🚫 All periods failed for {symbol}")
                
        except Exception as e:
            print(f"   🚫 Ticker creation failed: {e}")

def calculate_zones_nifsel_method(instrument_name, calculation_type="Weekly"):
    """
    EXACT zone calculation from NIFSEL.py
    """
    print(f"\n🔬 NIFSEL.py Zone Calculation: {instrument_name} ({calculation_type})")
    print("=" * 60)
    
    TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    
    if instrument_name not in TICKERS:
        print(f"❌ Instrument {instrument_name} not supported")
        return None, None
        
    ticker_symbol = TICKERS[instrument_name]
    
    # EXACT period logic from NIFSEL.py
    if calculation_type == "Weekly" and instrument_name == "NIFTY":
        period = "6mo"
    else:
        period = "5y"
        
    print(f"📊 Fetching {period} data for {ticker_symbol}...")
    
    try:
        # Try multiple methods to get data
        df_zones = None
        
        methods = [
            lambda: yf.Ticker(ticker_symbol).history(period=period, interval="1d"),
            lambda: yf.download(ticker_symbol, period=period, interval="1d", progress=False),
            lambda: yf.Ticker(ticker_symbol).history(period="3mo", interval="1d"),  # Fallback
        ]
        
        for i, method in enumerate(methods):
            try:
                df_zones = method()
                if df_zones is not None and not df_zones.empty:
                    print(f"✅ Method {i+1} successful: {len(df_zones)} records")
                    break
                else:
                    print(f"⚠️ Method {i+1}: Empty data")
            except Exception as e:
                print(f"❌ Method {i+1} failed: {e}")
        
        if df_zones is None or df_zones.empty:
            print(f"🚫 ALL methods failed for {ticker_symbol}")
            return None, None
            
        print(f"📈 Data range: {df_zones.index[0]} to {df_zones.index[-1]}")
        print(f"   Latest close: ₹{df_zones['Close'].iloc[-1]:.2f}")
        
        # Convert index to datetime
        df_zones.index = pd.to_datetime(df_zones.index)
        
        # EXACT resampling logic from NIFSEL.py
        resample_period = 'W' if calculation_type == "Weekly" else 'ME'
        agg_df = df_zones.resample(resample_period).agg({
            'Open': 'first', 
            'High': 'max', 
            'Low': 'min'
        }).dropna()
        
        print(f"📊 Resampled to {len(agg_df)} {calculation_type.lower()} periods")
        
        if len(agg_df) < 5:
            print(f"⚠️ Warning: Only {len(agg_df)} periods (recommended: 10+)")
            
        # Show latest period data
        print(f"   Latest period:")
        print(f"     Open: ₹{agg_df['Open'].iloc[-1]:.2f}")
        print(f"     High: ₹{agg_df['High'].iloc[-1]:.2f}")
        print(f"     Low: ₹{agg_df['Low'].iloc[-1]:.2f}")
        print(f"     Range: ₹{agg_df['High'].iloc[-1] - agg_df['Low'].iloc[-1]:.2f}")
            
        # EXACT rolling range calculation from NIFSEL.py
        periods_available = len(agg_df)
        rng5_periods = min(5, periods_available)
        rng10_periods = min(10, periods_available)
        
        rng5 = (agg_df['High'] - agg_df['Low']).rolling(rng5_periods).mean()
        rng10 = (agg_df['High'] - agg_df['Low']).rolling(rng10_periods).mean()
        
        # EXACT base price logic from NIFSEL.py
        base = agg_df['Open']
        
        print(f"\n🧮 Zone Calculation Details:")
        print(f"   Base (Open): ₹{base.iloc[-1]:.2f}")
        print(f"   RNG{rng5_periods} (avg range): ₹{rng5.iloc[-1]:.2f}")
        print(f"   RNG{rng10_periods} (avg range): ₹{rng10.iloc[-1]:.2f}")
        
        # EXACT zone calculation from NIFSEL.py
        u1 = base + 0.5 * rng5  # Upper zone 1
        u2 = base + 0.5 * rng10  # Upper zone 2
        l1 = base - 0.5 * rng5   # Lower zone 1
        l2 = base - 0.5 * rng10  # Lower zone 2
        
        print(f"\n📊 Zone Components:")
        print(f"   U1 (base + 0.5*rng{rng5_periods}): ₹{u1.iloc[-1]:.2f}")
        print(f"   U2 (base + 0.5*rng{rng10_periods}): ₹{u2.iloc[-1]:.2f}")
        print(f"   L1 (base - 0.5*rng{rng5_periods}): ₹{l1.iloc[-1]:.2f}")
        print(f"   L2 (base - 0.5*rng{rng10_periods}): ₹{l2.iloc[-1]:.2f}")
        
        # Get the latest zones
        latest_zones = pd.DataFrame({
            'u1': u1, 
            'u2': u2, 
            'l1': l1, 
            'l2': l2
        }).dropna().iloc[-1]
        
        # EXACT supply/demand calculation from NIFSEL.py
        supply_zone = round(max(latest_zones['u1'], latest_zones['u2']), 2)
        demand_zone = round(min(latest_zones['l1'], latest_zones['l2']), 2)
        
        print(f"\n✅ FINAL ZONES (NIFSEL.py method):")
        print(f"   Supply Zone: ₹{supply_zone:,} (max of U1, U2)")
        print(f"   Demand Zone: ₹{demand_zone:,} (min of L1, L2)")
        print(f"   Zone Range: ₹{supply_zone - demand_zone:,.2f}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ Error in NIFSEL.py zone calculation: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def calculate_zones_percentage_method(instrument_name):
    """
    Calculate zones using percentage method (fallback)
    """
    print(f"\n📊 Percentage-Based Zone Calculation: {instrument_name}")
    print("=" * 50)
    
    # Use mock current price for testing
    current_price = 24631.3 if instrument_name == "NIFTY" else 51500.0
    
    print(f"📈 Current Price (mock): ₹{current_price:,}")
    
    if instrument_name == "NIFTY":
        supply_zone = round(current_price * 1.053, 2)  # 5.3% above
        demand_zone = round(current_price * 0.946, 2)  # 5.4% below
        print(f"   Using NIFTY percentages: +5.3% / -5.4%")
    elif instrument_name == "BANKNIFTY":
        supply_zone = round(current_price * 1.06, 2)   # 6% above  
        demand_zone = round(current_price * 0.94, 2)   # 6% below
        print(f"   Using BANKNIFTY percentages: +6% / -6%")
    else:
        supply_zone = round(current_price * 1.055, 2)  # 5.5% above
        demand_zone = round(current_price * 0.945, 2)  # 5.5% below
        print(f"   Using default percentages: +5.5% / -5.5%")
    
    print(f"\n✅ FINAL ZONES (Percentage method):")
    print(f"   Supply Zone: ₹{supply_zone:,}")
    print(f"   Demand Zone: ₹{demand_zone:,}")
    print(f"   Zone Range: ₹{supply_zone - demand_zone:,.2f}")
    
    return supply_zone, demand_zone

def analyze_strike_selection_logic(instrument_name, supply_zone, demand_zone):
    """
    Demonstrate strike selection logic from NIFSEL.py without needing live option data
    """
    print(f"\n🎯 Strike Selection Logic: {instrument_name}")
    print("=" * 50)
    
    print(f"📊 Input zones:")
    print(f"   Supply Zone: ₹{supply_zone:,}")
    print(f"   Demand Zone: ₹{demand_zone:,}")
    
    # Configuration
    lot_size = 75 if instrument_name == "NIFTY" else 15
    strike_increment = 50 if instrument_name == "NIFTY" else 100
    
    print(f"\n⚙️ Configuration:")
    print(f"   Lot Size: {lot_size}")
    print(f"   Strike Increment: {strike_increment}")
    
    # CE Strike Selection (EXACT from NIFSEL.py)
    ce_high = math.ceil(supply_zone / strike_increment) * strike_increment
    strikes_ce = [ce_high, ce_high + strike_increment, ce_high + (2 * strike_increment)]
    
    print(f"\n📈 CE Strike Selection:")
    print(f"   Supply Zone: ₹{supply_zone}")
    print(f"   CE High (ceil to {strike_increment}): {ce_high}")
    print(f"   CE Strikes: {strikes_ce}")
    print(f"   Logic: ceil(supply_zone / {strike_increment}) * {strike_increment}")
    
    # PE Strike Selection (EXACT from NIFSEL.py)
    pe_high = math.floor(demand_zone / strike_increment) * strike_increment
    
    print(f"\n📉 PE Strike Selection:")
    print(f"   Demand Zone: ₹{demand_zone}")
    print(f"   PE High (floor to {strike_increment}): {pe_high}")
    print(f"   Logic: floor(demand_zone / {strike_increment}) * {strike_increment}")
    
    # Simulated PE strike selection (without live data)
    pe_mid = pe_high - strike_increment
    pe_low = pe_high - (2 * strike_increment)
    strikes_pe = [pe_high, pe_mid, pe_low]
    
    print(f"   PE Strikes: {strikes_pe}")
    print(f"   Note: In live system, PE Mid/Low are selected based on premium ranking")
    
    # Create mock strategy table
    mock_premiums_ce = [45.0, 30.0, 18.0]  # Mock CE premiums
    mock_premiums_pe = [42.0, 55.0, 75.0]  # Mock PE premiums
    
    print(f"\n📋 Mock Strategy Table:")
    print("=" * 70)
    print(f"{'Entry':<12} {'CE Strike':<10} {'CE Price':<10} {'PE Strike':<10} {'PE Price':<10} {'Combined':<10}")
    print("-" * 70)
    
    strategies = ["High Reward", "Mid Reward", "Low Reward"]
    for i, strategy in enumerate(strategies):
        ce_strike = strikes_ce[i]
        pe_strike = strikes_pe[i]
        ce_price = mock_premiums_ce[i]
        pe_price = mock_premiums_pe[i]
        combined = ce_price + pe_price
        
        print(f"{strategy:<12} {ce_strike:<10} ₹{ce_price:<9.2f} {pe_strike:<10} ₹{pe_price:<9.2f} ₹{combined:<9.2f}")
        
        # Calculate position details
        premium_received = combined * lot_size
        target_sl = premium_received * 0.8
        
        print(f"   → Premium: ₹{premium_received:,.0f}, Target/SL: ₹{target_sl:,.0f}")
    
    return {
        'ce_strikes': strikes_ce,
        'pe_strikes': strikes_pe,
        'lot_size': lot_size,
        'strike_increment': strike_increment
    }

def compare_zone_methods(instrument_name):
    """
    Compare different zone calculation methods
    """
    print(f"\n🔄 Comparing Zone Calculation Methods for {instrument_name}")
    print("=" * 70)
    
    results = {}
    
    # Method 1: NIFSEL.py exact method
    try:
        supply1, demand1 = calculate_zones_nifsel_method(instrument_name, "Weekly")
        if supply1 and demand1:
            results['NIFSEL.py'] = {'supply': supply1, 'demand': demand1}
    except Exception as e:
        print(f"❌ NIFSEL.py method failed: {e}")
    
    # Method 2: Percentage-based method
    try:
        supply2, demand2 = calculate_zones_percentage_method(instrument_name)
        if supply2 and demand2:
            results['Percentage'] = {'supply': supply2, 'demand': demand2}
    except Exception as e:
        print(f"❌ Percentage method failed: {e}")
    
    # Compare results
    print(f"\n📊 ZONE CALCULATION COMPARISON:")
    print("=" * 50)
    
    if results:
        print(f"{'Method':<15} {'Supply Zone':<15} {'Demand Zone':<15} {'Range':<10}")
        print("-" * 55)
        
        for method, zones in results.items():
            supply = zones['supply']
            demand = zones['demand']
            range_val = supply - demand
            print(f"{method:<15} ₹{supply:>12,} ₹{demand:>13,} ₹{range_val:>8,.0f}")
        
        # Show differences if we have multiple methods
        if len(results) > 1:
            methods = list(results.keys())
            supply_diff = abs(results[methods[0]]['supply'] - results[methods[1]]['supply'])
            demand_diff = abs(results[methods[0]]['demand'] - results[methods[1]]['demand'])
            
            print(f"\n📈 Differences:")
            print(f"   Supply Zone diff: ₹{supply_diff:,.2f}")
            print(f"   Demand Zone diff: ₹{demand_diff:,.2f}")
    
    return results

def main():
    """Main function to test and compare different approaches"""
    print("🧪 FIFTO Zone Calculation & Strike Selection Analysis")
    print("=" * 80)
    
    # Test data availability first
    test_yfinance_data_availability()
    
    # Test instruments
    instruments = ["NIFTY", "BANKNIFTY"]
    
    for instrument in instruments:
        print(f"\n\n🔬 ANALYZING {instrument}")
        print("=" * 80)
        
        # Compare zone calculation methods
        zone_results = compare_zone_methods(instrument)
        
        # If we have zones, demonstrate strike selection
        if zone_results:
            # Use the first available zone calculation
            method_name = list(zone_results.keys())[0]
            zones = zone_results[method_name]
            
            print(f"\n🎯 Using {method_name} zones for strike selection demo:")
            strike_results = analyze_strike_selection_logic(
                instrument, 
                zones['supply'], 
                zones['demand']
            )

if __name__ == "__main__":
    main()
