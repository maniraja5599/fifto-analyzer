#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('c:/Users/manir/Desktop/New folder/Django/fifto_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

# Setup Django
django.setup()

from analyzer.utils import calculate_weekly_zones, generate_analysis

def test_weekly_zones():
    print("🧪 Testing Weekly Supply/Demand Zone Calculation")
    print("=" * 50)
    
    instruments = ['NIFTY', 'BANKNIFTY']
    calculation_types = ['Weekly', 'Monthly']
    
    for instrument in instruments:
        print(f"\n📊 {instrument} Analysis:")
        print("-" * 30)
        
        for calc_type in calculation_types:
            print(f"\n{calc_type} Zones:")
            try:
                supply_zone, demand_zone = calculate_weekly_zones(instrument, calc_type)
                
                if supply_zone and demand_zone:
                    print(f"  ✅ Supply Zone: ₹{supply_zone:,.2f}")
                    print(f"  ✅ Demand Zone: ₹{demand_zone:,.2f}")
                    print(f"  📏 Zone Range: ₹{supply_zone - demand_zone:,.2f}")
                    
                    # Test strike calculation with zones
                    strike_increment = 50 if instrument == "NIFTY" else 100
                    
                    # CE strike from supply zone
                    import math
                    ce_strike = math.ceil(supply_zone / strike_increment) * strike_increment
                    
                    # PE strike from demand zone  
                    pe_strike = math.floor(demand_zone / strike_increment) * strike_increment
                    
                    print(f"  🎯 Suggested CE Strike: {ce_strike}")
                    print(f"  🎯 Suggested PE Strike: {pe_strike}")
                    
                else:
                    print(f"  ❌ Zone calculation failed for {instrument} {calc_type}")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")

def test_full_analysis():
    print("\n\n🔬 Testing Full Analysis with Zones")
    print("=" * 50)
    
    test_cases = [
        ('NIFTY', 'Weekly', '30-Jan-2025'),
        ('BANKNIFTY', 'Weekly', '30-Jan-2025'),
    ]
    
    for instrument, calc_type, expiry in test_cases:
        print(f"\n📈 {instrument} {calc_type} Analysis for {expiry}:")
        print("-" * 40)
        
        try:
            result, status = generate_analysis(instrument, calc_type, expiry)
            print(f"Status: {status}")
            
            if result:
                if result.get('zone_based'):
                    print("✅ Zone-based analysis successful!")
                    print(f"Supply Zone: ₹{result['supply_zone']:,.2f}")
                    print(f"Demand Zone: ₹{result['demand_zone']:,.2f}")
                else:
                    print("⚠️ Fallback to price-based analysis")
                
                print("\nStrike Selection:")
                for trade in result['df_data'][:2]:  # Show first 2 entries
                    print(f"  {trade['Entry']}: CE {trade['CE Strike']} @ ₹{trade['CE Price']:.2f}, "
                          f"PE {trade['PE Strike']} @ ₹{trade['PE Price']:.2f}")
            else:
                print("❌ Analysis failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_weekly_zones()
    test_full_analysis()
    print("\n✅ Testing completed!")
