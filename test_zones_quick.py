#!/usr/bin/env python
"""
Quick test to verify zone calculation is working correctly
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer.utils import calculate_weekly_zones

def test_zones():
    print("🧪 Testing zone calculation...")
    
    try:
        # Test zone calculation
        supply_zone, demand_zone = calculate_weekly_zones('NIFTY', '6mo')
        
        print(f"📊 Zone calculation results:")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        
        if supply_zone and demand_zone:
            print("✅ Zones calculated successfully!")
            return True
        else:
            print("❌ Zone calculation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error in zone calculation: {e}")
        return False

if __name__ == "__main__":
    test_zones()
