#!/usr/bin/env python3
"""
Comprehensive test comparing TradingView vs Legacy NIFSEL methods
"""
import sys
import os
import django

# Add the project path
sys.path.append('/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer.utils import try_yfinance_zones
import pandas as pd

def test_both_methods():
    """Compare TradingView vs Legacy NIFSEL methods"""
    print("🔄 Comprehensive Comparison: TradingView vs Legacy NIFSEL")
    print("=" * 80)
    
    instruments = ["NIFTY", "BANKNIFTY"]
    calculation_types = ["Weekly", "Monthly"]
    
    for instrument in instruments:
        for calc_type in calculation_types:
            print(f"\n📊 Testing {calc_type} {instrument}")
            print("-" * 60)
            
            # Test TradingView method
            print(f"\n🎯 TradingView Method:")
            tv_supply, tv_demand = try_yfinance_zones(instrument, calc_type, method="tradingview")
            
            if tv_supply and tv_demand:
                print(f"   ✅ TradingView Zones:")
                print(f"      Supply: ₹{tv_supply}")
                print(f"      Demand: ₹{tv_demand}")
                print(f"      Range: ₹{tv_supply - tv_demand:.2f}")
            else:
                print(f"   ❌ TradingView method failed")
            
            # Test Legacy method
            print(f"\n📜 Legacy NIFSEL Method:")
            leg_supply, leg_demand = try_yfinance_zones(instrument, calc_type, method="legacy")
            
            if leg_supply and leg_demand:
                print(f"   ✅ Legacy Zones:")
                print(f"      Supply: ₹{leg_supply}")
                print(f"      Demand: ₹{leg_demand}")
                print(f"      Range: ₹{leg_supply - leg_demand:.2f}")
            else:
                print(f"   ❌ Legacy method failed")
            
            # Compare results
            if tv_supply and tv_demand and leg_supply and leg_demand:
                supply_diff = abs(tv_supply - leg_supply)
                demand_diff = abs(tv_demand - leg_demand)
                range_diff = abs((tv_supply - tv_demand) - (leg_supply - leg_demand))
                
                print(f"\n🔍 Comparison:")
                print(f"   Supply Difference: ₹{supply_diff:.2f}")
                print(f"   Demand Difference: ₹{demand_diff:.2f}")
                print(f"   Range Difference: ₹{range_diff:.2f}")
                
                if supply_diff < 100 and demand_diff < 100:
                    print(f"   ✅ Methods are similar (difference < ₹100)")
                else:
                    print(f"   ⚠️ Methods show significant difference")

def show_method_differences():
    """Explain the differences between methods"""
    print("\n\n📋 Method Differences Summary")
    print("=" * 60)
    
    print("🎯 TradingView Method:")
    print("   • Uses timeframe-specific data (1d, 1wk, 1mo)")
    print("   • Previous candle ranges: high[1] - low[1]")
    print("   • Current candle open: open[0]")
    print("   • Direct SMA on range data")
    print("   • More accurate to TradingView indicator")
    
    print("\n📜 Legacy NIFSEL Method:")
    print("   • Uses daily data then resamples")
    print("   • Current period ranges: high - low")
    print("   • Resampled period open")
    print("   • SMA on resampled range data")
    print("   • Period-based (6mo for Weekly NIFTY, 5y others)")
    
    print("\n🎯 Recommendation:")
    print("   Use TradingView method for accuracy with TradingView charts")
    print("   Use Legacy method for compatibility with old NIFSEL.py")

if __name__ == "__main__":
    test_both_methods()
    show_method_differences()
