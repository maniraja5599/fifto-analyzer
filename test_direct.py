#!/usr/bin/env python
"""
Direct test of the generate_analysis function
"""
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils

def test_generate_analysis():
    print("🧪 Testing generate_analysis function directly...")
    print("=" * 50)
    
    # Test parameters
    instrument = "NIFTY"
    calc_type = "Weekly" 
    expiry = "07-Aug-2025"  # Next week's expiry
    
    print(f"Test parameters:")
    print(f"  Instrument: {instrument}")
    print(f"  Calc Type: {calc_type}")
    print(f"  Expiry: {expiry}")
    print()
    
    try:
        print("Calling utils.generate_analysis()...")
        result = utils.generate_analysis(instrument, calc_type, expiry)
        
        print(f"\nResult type: {type(result)}")
        if isinstance(result, tuple) and len(result) == 2:
            analysis_data, status = result
            print(f"Analysis data: {type(analysis_data)}")
            print(f"Status: {status}")
            
            if analysis_data:
                print("✅ SUCCESS: Analysis data generated")
                print(f"Keys in analysis_data: {list(analysis_data.keys()) if isinstance(analysis_data, dict) else 'Not a dict'}")
            else:
                print("❌ FAILED: No analysis data returned")
        else:
            print(f"❌ Unexpected result format: {result}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generate_analysis()
