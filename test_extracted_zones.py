#!/usr/bin/env python3
"""
Standalone test of zone calculation logic extracted from utils.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
import math
import requests
import time
from datetime import datetime

def calculate_weekly_zones_extracted(instrument_name, calculation_type):
    """
    Extracted zone calculation from utils.py (YFinance-only approach)
    """
    print(f"🔄 Testing extracted utils.py logic: {instrument_name} ({calculation_type})")
    print("-" * 60)
    
    try:
        # EXACT ticker mapping from utils.py
        TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        
        if instrument_name not in TICKERS:
            print(f"❌ Instrument {instrument_name} not supported")
            return None, None
            
        ticker_symbol = TICKERS[instrument_name]
        
        # EXACT period logic from utils.py
        if calculation_type == "Weekly" and instrument_name == "NIFTY":
            period = "6mo"  # EXACT from utils.py for Weekly NIFTY
        else:
            period = "5y"   # Default for other calculations
            
        # Fetch historical data with multiple attempts (from utils.py)
        print(f"📊 Fetching yfinance data for {ticker_symbol} with period {period}...")
        df_zones = None
        
        # Try multiple methods to get yfinance data (EXACT from utils.py)
        for attempt in range(3):
            try:
                if attempt == 0:
                    df_zones = yf.Ticker(ticker_symbol).history(period=period, interval="1d")
                elif attempt == 1:
                    # Try shorter period
                    df_zones = yf.Ticker(ticker_symbol).history(period="3mo", interval="1d")
                else:
                    # Try download method
                    df_zones = yf.download(ticker_symbol, period="1mo", interval="1d", progress=False)
                
                if df_zones is not None and not df_zones.empty:
                    print(f"✅ YFinance data (attempt {attempt+1}): {len(df_zones)} records")
                    break
                else:
                    print(f"⚠️ Attempt {attempt+1} returned empty data")
                    df_zones = None
                    
            except Exception as e:
                print(f"⚠️ Attempt {attempt+1} failed: {e}")
                df_zones = None
                continue
        
        if df_zones is None or df_zones.empty:
            print(f"❌ All yfinance attempts failed for {ticker_symbol}")
            print(f"🔄 Would fall back to percentage-based calculation...")
            return calculate_percentage_based_zones_extracted(instrument_name)
        
        print(f"✅ yfinance data: {len(df_zones)} records from {df_zones.index[0]} to {df_zones.index[-1]}")
        
        # Convert index to datetime (EXACT from utils.py)
        df_zones.index = pd.to_datetime(df_zones.index)
        
        # EXACT resampling logic from utils.py
        resample_period = 'W' if calculation_type == "Weekly" else 'ME'
        agg_df = df_zones.resample(resample_period).agg({
            'Open': 'first', 
            'High': 'max', 
            'Low': 'min'
        }).dropna()
        
        if len(agg_df) < 5:  # Reduced requirement from 10 to 5 (from utils.py)
            print(f"❌ Insufficient resampled data for {instrument_name} (need 5, got {len(agg_df)})")
            print(f"🔄 Would fall back to percentage-based calculation...")
            return calculate_percentage_based_zones_extracted(instrument_name)
            
        print(f"✅ Resampled to {len(agg_df)} periods for zone calculation")
        
        # EXACT rolling range calculation from utils.py
        rng5 = (agg_df['High'] - agg_df['Low']).rolling(min(5, len(agg_df))).mean()
        rng10 = (agg_df['High'] - agg_df['Low']).rolling(min(10, len(agg_df))).mean()
        
        # EXACT base price logic from utils.py
        base = agg_df['Open']
        
        # EXACT zone calculation from utils.py
        u1 = base + 0.5 * rng5  # Upper zone 1
        u2 = base + 0.5 * rng10  # Upper zone 2
        l1 = base - 0.5 * rng5   # Lower zone 1
        l2 = base - 0.5 * rng10  # Lower zone 2
        
        # Get the latest zones (EXACT from utils.py)
        latest_zones = pd.DataFrame({
            'u1': u1, 
            'u2': u2, 
            'l1': l1, 
            'l2': l2
        }).dropna()
        
        if latest_zones.empty:
            print(f"❌ No zone data calculated from yfinance")
            print(f"🔄 Would fall back to percentage-based calculation...")
            return calculate_percentage_based_zones_extracted(instrument_name)
            
        latest = latest_zones.iloc[-1]
        
        # EXACT supply/demand calculation from utils.py
        supply_zone = round(max(latest['u1'], latest['u2']), 2)
        demand_zone = round(min(latest['l1'], latest['l2']), 2)
        
        print(f"✅ utils.py zones calculated for {instrument_name} ({calculation_type}):")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        print(f"   Zone Range: ₹{supply_zone - demand_zone:.2f}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ utils.py zone calculation failed for {instrument_name}: {e}")
        print(f"🔄 Would fall back to percentage-based calculation...")
        return calculate_percentage_based_zones_extracted(instrument_name)

def calculate_percentage_based_zones_extracted(instrument_name):
    """
    Extracted percentage-based zone calculation from utils.py
    """
    try:
        # Mock current price (since we can't access option chain easily)
        current_price = 24631.3 if instrument_name == "NIFTY" else 55341.85
            
        print(f"📊 utils.py percentage-based zones for {instrument_name}")
        print(f"   Current Price: ₹{current_price:,.2f}")
        
        # Calculate zones as percentage of current price (EXACT from utils.py)
        if instrument_name == "NIFTY":
            supply_zone = round(current_price * 1.053, 2)  # 5.3% above
            demand_zone = round(current_price * 0.946, 2)  # 5.4% below
        elif instrument_name == "BANKNIFTY":
            supply_zone = round(current_price * 1.06, 2)   # 6% above  
            demand_zone = round(current_price * 0.94, 2)   # 6% below
        else:
            supply_zone = round(current_price * 1.055, 2)  # 5.5% above
            demand_zone = round(current_price * 0.945, 2)  # 5.5% below
        
        print(f"✅ utils.py percentage-based zones for {instrument_name}:")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        print(f"   Zone Range: ₹{supply_zone - demand_zone:.2f}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ utils.py percentage-based zone calculation failed: {e}")
        return None, None

def compare_all_methods():
    """
    Compare NIFSEL.py vs utils.py vs percentage methods
    """
    print("🔄 COMPLETE METHOD COMPARISON")
    print("=" * 80)
    
    # Reference results from previous NIFSEL.py run
    nifsel_results = {
        'NIFTY': {'supply': 24607.53, 'demand': 24135.47},
        'BANKNIFTY': {'supply': 55547.80, 'demand': 54450.90}
    }
    
    for instrument in ['NIFTY', 'BANKNIFTY']:
        print(f"\n📊 {instrument} - All Methods Comparison:")
        print("=" * 60)
        
        # Test current utils.py logic
        utils_supply, utils_demand = calculate_weekly_zones_extracted(instrument, "Weekly")
        
        # Test percentage method
        pct_supply, pct_demand = calculate_percentage_based_zones_extracted(instrument)
        
        # Comparison table
        print(f"\n📈 COMPARISON RESULTS:")
        print(f"{'Method':<20} {'Supply Zone':<15} {'Demand Zone':<15} {'Range':<12}")
        print("-" * 65)
        
        # NIFSEL.py reference
        ref = nifsel_results[instrument]
        ref_range = ref['supply'] - ref['demand']
        print(f"{'NIFSEL.py':<20} ₹{ref['supply']:>13,.2f} ₹{ref['demand']:>13,.2f} ₹{ref_range:>10,.0f}")
        
        # utils.py method
        if utils_supply and utils_demand:
            utils_range = utils_supply - utils_demand
            print(f"{'utils.py':<20} ₹{utils_supply:>13,.2f} ₹{utils_demand:>13,.2f} ₹{utils_range:>10,.0f}")
            
            # Show differences from NIFSEL.py
            supply_diff = abs(utils_supply - ref['supply'])
            demand_diff = abs(utils_demand - ref['demand'])
            print(f"{'  vs NIFSEL.py':<20} ₹{supply_diff:>13,.2f} ₹{demand_diff:>13,.2f}")
        
        # Percentage method
        if pct_supply and pct_demand:
            pct_range = pct_supply - pct_demand
            print(f"{'Percentage':<20} ₹{pct_supply:>13,.2f} ₹{pct_demand:>13,.2f} ₹{pct_range:>10,.0f}")
            
            # Show differences from NIFSEL.py
            supply_diff_pct = abs(pct_supply - ref['supply'])
            demand_diff_pct = abs(pct_demand - ref['demand'])
            print(f"{'  vs NIFSEL.py':<20} ₹{supply_diff_pct:>13,.2f} ₹{demand_diff_pct:>13,.2f}")

def main():
    print("🧪 Complete Zone Calculation Analysis")
    print("Testing NIFSEL.py vs utils.py vs Percentage methods")
    print("=" * 80)
    
    compare_all_methods()
    
    print(f"\n💡 KEY INSIGHTS:")
    print("=" * 40)
    print("1. NIFSEL.py uses 6mo data for NIFTY Weekly, 5y for others")
    print("2. utils.py has YFinance retry logic with percentage fallback")
    print("3. Percentage method provides wide but reliable zones")
    print("4. YFinance data availability is inconsistent")
    print("5. Zone ranges vary significantly between methods")

if __name__ == "__main__":
    main()
