#!/usr/bin/env python3
"""
Debug script to understand the analysis data structure
"""
import os
import sys
import json

# Set up Django
project_dir = r"c:\Users\manir\Desktop\New folder\Django\fifto_project"
sys.path.append(project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

import django
django.setup()

from analyzer import utils

def debug_analysis_data():
    print("🔍 DEBUGGING ANALYSIS DATA STRUCTURE")
    print("=" * 50)
    
    # Check if there are any existing trades
    trades = utils.load_trades()
    print(f"📊 Current trades count: {len(trades)}")
    
    if trades:
        print("📋 Existing trades:")
        for i, trade in enumerate(trades):
            print(f"  {i+1}. ID: {trade.get('id', 'NO_ID')}")
            print(f"      Status: {trade.get('status', 'NO_STATUS')}")
            print(f"      Tag: {trade.get('entry_tag', 'NO_TAG')}")
    
    # Create a sample analysis similar to what might be generated
    sample_analysis = {
        'instrument': 'NIFTY',
        'expiry': '07-Aug-2025',
        'df_data': [
            {
                'Entry': 'Short Straddle',
                'CE Strike': 24500,
                'PE Strike': 24500, 
                'Combined Premium': 150.0,
                'Target': 75.0,
                'Stoploss': 300.0
            },
            {
                'Entry': 'Iron Condor',
                'CE Strike': 24600,
                'PE Strike': 24400,
                'Combined Premium': 100.0,
                'Target': 50.0,
                'Stoploss': 200.0
            },
            {
                'Entry': 'Bull Call Spread',
                'CE Strike': 24400,
                'PE Strike': 24500,
                'Combined Premium': 80.0,
                'Target': 40.0,
                'Stoploss': 160.0
            }
        ]
    }
    
    print(f"\n📈 Testing with sample analysis data:")
    print(f"   Instrument: {sample_analysis['instrument']}")
    print(f"   Expiry: {sample_analysis['expiry']}")
    print(f"   Strategies count: {len(sample_analysis['df_data'])}")
    
    for i, entry in enumerate(sample_analysis['df_data']):
        print(f"\n   Strategy {i+1}: {entry['Entry']}")
        trade_id = f"{sample_analysis['instrument']}_{sample_analysis['expiry']}_{entry['Entry'].replace(' ', '')}"
        print(f"   Generated ID: {trade_id}")
    
    # Test the add_to_analysis function
    print(f"\n🧪 Testing add_to_analysis function:")
    initial_count = len(trades)
    
    try:
        result = utils.add_to_analysis(sample_analysis)
        print(f"   Result: {result}")
        
        # Check trades after
        trades_after = utils.load_trades()
        final_count = len(trades_after)
        
        print(f"   Trades before: {initial_count}")
        print(f"   Trades after: {final_count}")
        print(f"   New trades added: {final_count - initial_count}")
        
        if final_count > initial_count:
            print("   ✅ SUCCESS: Trades were added!")
            new_trades = trades_after[initial_count:]
            for trade in new_trades:
                print(f"      - {trade['id']} | {trade['status']} | {trade['entry_tag']}")
        else:
            print("   ❌ ISSUE: No trades were added")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_analysis_data()
