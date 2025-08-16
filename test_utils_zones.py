#!/usr/bin/env python3
"""
Test the current utils.py zone calculation to see how it compares
"""

import sys
import os
from datetime import datetime

# Add the analyzer module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'analyzer'))

def test_current_utils_zones():
    """Test the current zone calculation from utils.py"""
    
    try:
        # Import our current utils functions
        from utils import calculate_weekly_zones, calculate_percentage_based_zones
        
        print("🔬 Testing Current utils.py Zone Calculations")
        print("=" * 60)
        
        instruments = ["NIFTY", "BANKNIFTY"]
        
        for instrument in instruments:
            print(f"\n📊 Testing {instrument} with current utils.py:")
            print("-" * 40)
            
            # Test current weekly zones calculation (which tries yfinance first)
            try:
                supply, demand = calculate_weekly_zones(instrument, "Weekly")
                if supply and demand:
                    print(f"✅ utils.py calculate_weekly_zones():")
                    print(f"   Supply Zone: ₹{supply:,}")
                    print(f"   Demand Zone: ₹{demand:,}")
                    print(f"   Range: ₹{supply - demand:,.2f}")
                else:
                    print(f"❌ utils.py calculate_weekly_zones() returned None")
            except Exception as e:
                print(f"❌ utils.py calculate_weekly_zones() failed: {e}")
            
            # Test percentage-based zones
            try:
                supply_pct, demand_pct = calculate_percentage_based_zones(instrument)
                if supply_pct and demand_pct:
                    print(f"✅ utils.py calculate_percentage_based_zones():")
                    print(f"   Supply Zone: ₹{supply_pct:,}")
                    print(f"   Demand Zone: ₹{demand_pct:,}")
                    print(f"   Range: ₹{supply_pct - demand_pct:,.2f}")
                else:
                    print(f"❌ utils.py calculate_percentage_based_zones() returned None")
            except Exception as e:
                print(f"❌ utils.py calculate_percentage_based_zones() failed: {e}")
                
    except ImportError as e:
        print(f"❌ Could not import utils.py functions: {e}")
        print("   Make sure utils.py is in the analyzer directory")

def test_all_methods_comparison():
    """Compare all available zone calculation methods"""
    
    print("\n\n🔄 COMPREHENSIVE ZONE CALCULATION COMPARISON")
    print("=" * 80)
    
    # Results storage
    results = {
        'NIFTY': {},
        'BANKNIFTY': {}
    }
    
    # Test each instrument
    for instrument in ['NIFTY', 'BANKNIFTY']:
        print(f"\n📊 {instrument} Zone Comparison:")
        print("-" * 50)
        
        # Method 1: Try current utils.py
        try:
            from utils import calculate_weekly_zones
            supply, demand = calculate_weekly_zones(instrument, "Weekly")
            if supply and demand:
                results[instrument]['utils.py'] = {'supply': supply, 'demand': demand}
                print(f"✅ utils.py method: Supply ₹{supply:,}, Demand ₹{demand:,}")
            else:
                print(f"❌ utils.py method failed")
        except Exception as e:
            print(f"❌ utils.py method error: {e}")
        
        # Method 2: Percentage fallback
        try:
            from utils import calculate_percentage_based_zones
            supply_pct, demand_pct = calculate_percentage_based_zones(instrument)
            if supply_pct and demand_pct:
                results[instrument]['Percentage'] = {'supply': supply_pct, 'demand': demand_pct}
                print(f"✅ Percentage method: Supply ₹{supply_pct:,}, Demand ₹{demand_pct:,}")
        except Exception as e:
            print(f"❌ Percentage method error: {e}")
    
    # Summary comparison
    print(f"\n📈 FINAL COMPARISON TABLE:")
    print("=" * 80)
    
    for instrument in ['NIFTY', 'BANKNIFTY']:
        print(f"\n{instrument}:")
        print(f"{'Method':<20} {'Supply Zone':<15} {'Demand Zone':<15} {'Range':<12}")
        print("-" * 65)
        
        if instrument in results:
            for method, zones in results[instrument].items():
                supply = zones['supply']
                demand = zones['demand']
                range_val = supply - demand
                print(f"{method:<20} ₹{supply:>13,} ₹{demand:>13,} ₹{range_val:>10,.0f}")
        
        # Add NIFSEL reference from previous run
        if instrument == 'NIFTY':
            print(f"{'NIFSEL.py (ref)':<20} ₹{'24,607.53':>13} ₹{'24,135.47':>13} ₹{'472':>10}")
        elif instrument == 'BANKNIFTY':
            print(f"{'NIFSEL.py (ref)':<20} ₹{'55,547.80':>13} ₹{'54,450.90':>13} ₹{'1,097':>10}")

if __name__ == "__main__":
    test_current_utils_zones()
    test_all_methods_comparison()
