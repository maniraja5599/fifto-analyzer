#!/usr/bin/env python3
"""
Test script to debug portfolio addition issue
"""
import os
import sys
import django

# Add the Django project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils
import json

def test_portfolio_functionality():
    print("=== Portfolio Addition Debug Test ===")
    
    # Check current trades
    print("\n1. Checking current trades...")
    trades = utils.load_trades()
    print(f"Current trades count: {len(trades)}")
    if trades:
        print("Existing trades:")
        for trade in trades[-3:]:  # Show last 3 trades
            print(f"  - ID: {trade['id']}, Tag: {trade['entry_tag']}, Status: {trade['status']}")
    else:
        print("  No existing trades found")
    
    # Check if trades file exists
    print(f"\n2. Trades file location: {utils.TRADES_DB_FILE}")
    print(f"   File exists: {os.path.exists(utils.TRADES_DB_FILE)}")
    
    # Create a sample analysis data to test with
    print("\n3. Creating sample analysis data...")
    sample_analysis = {
        'instrument': 'NIFTY',
        'expiry': '06-Feb-2025',
        'df_data': [
            {
                'Entry': 'Short Straddle',
                'CE Strike': 23200,
                'PE Strike': 23200,
                'Combined Premium': 150.0,
                'Target': 75.0,
                'Stoploss': 225.0
            }
        ]
    }
    
    print("Sample analysis data created")
    
    # Test the add_to_analysis function
    print("\n4. Testing add_to_analysis function...")
    result = utils.add_to_analysis(sample_analysis)
    print(f"Result: {result}")
    
    # Check trades again
    print("\n5. Checking trades after addition...")
    trades_after = utils.load_trades()
    print(f"Trades count after addition: {len(trades_after)}")
    if len(trades_after) > len(trades):
        print("✅ New trade was added successfully!")
        new_trade = trades_after[-1]
        print(f"New trade details:")
        print(f"  - ID: {new_trade['id']}")
        print(f"  - Tag: {new_trade['entry_tag']}")
        print(f"  - Instrument: {new_trade['instrument']}")
        print(f"  - Status: {new_trade['status']}")
    else:
        print("❌ No new trade was added")
        print("This could be because a trade with the same ID already exists")
    
    # Test duplicate prevention
    print("\n6. Testing duplicate prevention...")
    result2 = utils.add_to_analysis(sample_analysis)
    print(f"Second addition result: {result2}")
    
    trades_after2 = utils.load_trades()
    if len(trades_after2) == len(trades_after):
        print("✅ Duplicate prevention working correctly")
    else:
        print("❌ Duplicate was added (this shouldn't happen)")

if __name__ == "__main__":
    test_portfolio_functionality()
