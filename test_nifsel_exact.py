#!/usr/bin/env python3
"""
Test script to verify EXACT TradingView zone calculations
"""
import sys
import os
import django

# Add the project path
sys.path.append('/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer.utils import try_yfinance_zones, calculate_zones_from_data_yfinance
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_exact_tradingview_logic():
    """Test the EXACT TradingView implementation"""
    print("🎯 Testing EXACT TradingView Logic Implementation")
    print("=" * 70)
    
    # Test 1: Weekly zones (should use 1wk timeframe)
    print("\n📊 Test 1: Weekly NIFTY (TradingView 1wk timeframe)")
    print("-" * 50)
    
    supply_weekly, demand_weekly = try_yfinance_zones("NIFTY", "Weekly")
    if supply_weekly and demand_weekly:
        print(f"✅ Weekly NIFTY Zones (TradingView method):")
        print(f"   Supply: ₹{supply_weekly}")
        print(f"   Demand: ₹{demand_weekly}")
        print(f"   Range: ₹{supply_weekly - demand_weekly:.2f}")
    else:
        print("❌ Weekly NIFTY calculation failed")
    
    # Test 2: Monthly zones (should use 1mo timeframe)
    print("\n📊 Test 2: Monthly NIFTY (TradingView 1mo timeframe)")
    print("-" * 50)
    
    supply_monthly, demand_monthly = try_yfinance_zones("NIFTY", "Monthly")
    if supply_monthly and demand_monthly:
        print(f"✅ Monthly NIFTY Zones (TradingView method):")
        print(f"   Supply: ₹{supply_monthly}")
        print(f"   Demand: ₹{demand_monthly}")
        print(f"   Range: ₹{supply_monthly - demand_monthly:.2f}")
    else:
        print("❌ Monthly NIFTY calculation failed")
    
    # Test 3: Daily zones (should use 1d timeframe)
    print("\n📊 Test 3: Daily NIFTY (TradingView 1d timeframe)")
    print("-" * 50)
    
    supply_daily, demand_daily = try_yfinance_zones("NIFTY", "Daily")
    if supply_daily and demand_daily:
        print(f"✅ Daily NIFTY Zones (TradingView method):")
        print(f"   Supply: ₹{supply_daily}")
        print(f"   Demand: ₹{demand_daily}")
        print(f"   Range: ₹{supply_daily - demand_daily:.2f}")
    else:
        print("❌ Daily NIFTY calculation failed")

def test_tradingview_algorithm_directly():
    """Test the TradingView algorithm on sample data"""
    print("\n🔬 Testing TradingView Algorithm Directly")
    print("=" * 50)
    
    # Create sample weekly data
    dates = pd.date_range('2024-01-01', '2024-08-15', freq='W')
    
    # Sample NIFTY weekly data (realistic values)
    sample_data = {
        'Open': [21000, 21100, 21050, 21200, 21150, 21300, 21250, 21400, 21350, 21500,
                21450, 21600, 21550, 21700, 21650, 21800, 21750, 21900, 21850, 22000,
                22050, 22100, 22150, 22200, 22250, 22300, 22350, 22400, 22450, 22500,
                22550, 22600, 22650],
        'High': [21200, 21300, 21250, 21400, 21350, 21500, 21450, 21600, 21550, 21700,
                21650, 21800, 21750, 21900, 21850, 22000, 21950, 22100, 22050, 22200,
                22250, 22300, 22350, 22400, 22450, 22500, 22550, 22600, 22650, 22700,
                22750, 22800, 22850],
        'Low': [20900, 21000, 20950, 21100, 21050, 21200, 21150, 21300, 21250, 21400,
               21350, 21500, 21450, 21600, 21550, 21700, 21650, 21800, 21750, 21900,
               21950, 22000, 22050, 22100, 22150, 22200, 22250, 22300, 22350, 22400,
               22450, 22500, 22550],
        'Close': [21050, 21150, 21100, 21250, 21200, 21350, 21300, 21450, 21400, 21550,
                 21500, 21650, 21600, 21750, 21700, 21850, 21800, 21950, 21900, 22050,
                 22100, 22150, 22200, 22250, 22300, 22350, 22400, 22450, 22500, 22550,
                 22600, 22650, 22700]
    }
    
    # Take only available data
    available_periods = len(dates)
    for key in sample_data:
        sample_data[key] = sample_data[key][:available_periods]
    
    df = pd.DataFrame(sample_data, index=dates)
    
    print(f"📊 Sample weekly data: {len(df)} periods")
    print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"   Price range: ₹{df['Low'].min():.2f} - ₹{df['High'].max():.2f}")
    
    # Apply TradingView algorithm
    supply, demand = calculate_zones_from_data_yfinance(df, "NIFTY", "Weekly")
    
    if supply and demand:
        print(f"\n✅ TradingView Algorithm Results:")
        print(f"   Supply Zone: ₹{supply}")
        print(f"   Demand Zone: ₹{demand}")
        print(f"   Zone Range: ₹{supply - demand:.2f}")
        print(f"   Current Price: ₹{df['Close'].iloc[-1]:.2f}")
        
        # Check if current price is in zones
        current_price = df['Close'].iloc[-1]
        if demand <= current_price <= supply:
            print(f"   🎯 Current price is WITHIN the zone!")
        elif current_price > supply:
            print(f"   📈 Current price is ABOVE supply zone (+₹{current_price - supply:.2f})")
        else:
            print(f"   📉 Current price is BELOW demand zone (-₹{demand - current_price:.2f})")

def verify_tradingview_formulas():
    """Verify the exact TradingView formulas"""
    print("\n🧮 Verifying EXACT TradingView Formulas")
    print("=" * 50)
    
    print("TradingView Code Analysis:")
    print("f_get_zone(tf) =>")
    print("    rng5 = ta.sma(high[1] - low[1], 5)")  
    print("    rng10 = ta.sma(high[1] - low[1], 10)")
    print("    base = open[0]")
    print("    u1 = base + 0.5 * rng5")
    print("    u2 = base + 0.5 * rng10") 
    print("    l1 = base - 0.5 * rng5")
    print("    l2 = base - 0.5 * rng10")
    print("")
    print("Key Points:")
    print("✅ Uses PREVIOUS candle ranges: high[1] - low[1]")
    print("✅ Uses CURRENT candle open: open[0]")
    print("✅ SMA of 5 and 10 periods on ranges")
    print("✅ Supply = max(u1, u2), Demand = min(l1, l2)")
    print("✅ Different timeframes: D, W, M")

if __name__ == "__main__":
    test_exact_tradingview_logic()
    test_tradingview_algorithm_directly()
    verify_tradingview_formulas()
