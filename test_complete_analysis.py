#!/usr/bin/env python
"""
Test the fixed generate_analysis function
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer.utils import generate_analysis
from datetime import datetime, timedelta

def test_analysis():
    print("🧪 Testing complete analysis generation...")
    
    try:
        # Calculate next Thursday for weekly expiry
        today = datetime.now()
        days_ahead = 3 - today.weekday()  # Thursday is 3
        if days_ahead <= 0:  # Thursday already passed
            days_ahead += 7
        next_expiry = today + timedelta(days=days_ahead)
        expiry_str = next_expiry.strftime('%d-%b-%Y')
        
        print(f"📅 Testing with expiry: {expiry_str}")
        
        # Test analysis generation
        analysis_data, status_message = generate_analysis('NIFTY', 'Weekly', expiry_str)
        
        print(f"📊 Analysis result:")
        print(f"   Status: {status_message}")
        
        if analysis_data:
            print(f"   Data keys: {list(analysis_data.keys())}")
            print(f"   Dataframe entries: {len(analysis_data.get('df_data', []))}")
            print(f"   Supply zone: {analysis_data.get('supply_zone')}")
            print(f"   Demand zone: {analysis_data.get('demand_zone')}")
            print("✅ Analysis generated successfully!")
            return True
        else:
            print("❌ Analysis generation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error in analysis generation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_analysis()
