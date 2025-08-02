#!/usr/bin/env python3
"""
Portfolio Addition Investigation Script
"""
import os
import sys
import json
from datetime import datetime

# Set up paths
project_dir = r"c:\Users\manir\Desktop\New folder\Django\fifto_project"
sys.path.append(project_dir)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
import django
django.setup()

from analyzer import utils

def investigate_portfolio_issue():
    print("🔍 PORTFOLIO ADDITION INVESTIGATION")
    print("=" * 50)
    
    # 1. Check if trades file exists and its location
    print(f"\n1. Checking trades file:")
    print(f"   File path: {utils.TRADES_DB_FILE}")
    print(f"   File exists: {os.path.exists(utils.TRADES_DB_FILE)}")
    
    if os.path.exists(utils.TRADES_DB_FILE):
        try:
            with open(utils.TRADES_DB_FILE, 'r') as f:
                file_content = f.read()
                print(f"   File size: {len(file_content)} characters")
                if file_content.strip():
                    trades_data = json.loads(file_content)
                    print(f"   Number of trades: {len(trades_data)}")
                else:
                    print("   File is empty")
        except Exception as e:
            print(f"   Error reading file: {e}")
    
    # 2. Load trades using the utility function
    print(f"\n2. Loading trades using utils.load_trades():")
    trades = utils.load_trades()
    print(f"   Trades loaded: {len(trades)}")
    
    if trades:
        print("   Recent trades:")
        for i, trade in enumerate(trades[-3:]):
            print(f"     {i+1}. ID: {trade['id']}")
            print(f"        Status: {trade['status']}")
            print(f"        Tag: {trade.get('entry_tag', 'No tag')}")
            print(f"        Instrument: {trade.get('instrument', 'Unknown')}")
            print(f"        Start Time: {trade.get('start_time', 'Unknown')}")
            print()
    
    # 3. Check what statuses exist
    if trades:
        statuses = {}
        for trade in trades:
            status = trade.get('status', 'No Status')
            statuses[status] = statuses.get(status, 0) + 1
        
        print(f"3. Trade status breakdown:")
        for status, count in statuses.items():
            print(f"   {status}: {count} trades")
    
    # 4. Simulate adding a new trade
    print(f"\n4. Testing trade addition:")
    
    # Create sample analysis data
    test_analysis = {
        'instrument': 'NIFTY',
        'expiry': '06-Feb-2025',
        'df_data': [
            {
                'Entry': 'Test Portfolio',
                'CE Strike': 23200,
                'PE Strike': 23200,
                'Combined Premium': 150.0,
                'Target': 75.0,
                'Stoploss': 225.0
            }
        ]
    }
    
    print("   Sample analysis data created")
    
    # Test adding to portfolio
    initial_count = len(trades)
    result = utils.add_to_analysis(test_analysis)
    print(f"   Addition result: {result}")
    
    # Check if trade was added
    trades_after = utils.load_trades()
    final_count = len(trades_after)
    
    print(f"   Trades before: {initial_count}")
    print(f"   Trades after: {final_count}")
    
    if final_count > initial_count:
        print("   ✅ Trade was added successfully!")
        new_trade = trades_after[-1]
        print(f"   New trade details:")
        print(f"     ID: {new_trade['id']}")
        print(f"     Status: {new_trade['status']}")
        print(f"     Tag: {new_trade.get('entry_tag', 'No tag')}")
        
        # Check if it would be filtered as active
        if new_trade.get('status') == 'Running':
            print("   ✅ Trade has 'Running' status - should appear in Active Trades")
        else:
            print(f"   ❌ Trade has '{new_trade.get('status')}' status - will NOT appear in Active Trades")
    else:
        print("   ❌ No trade was added (likely duplicate)")
    
    # 5. Test the filtering logic
    print(f"\n5. Testing Active Trades filtering:")
    running_trades = [t for t in trades_after if t.get('status') == 'Running']
    print(f"   Trades with 'Running' status: {len(running_trades)}")
    
    if running_trades:
        print("   Running trades:")
        for trade in running_trades[-3:]:
            print(f"     - {trade['id']} | {trade.get('entry_tag', 'No tag')}")
    else:
        print("   No trades with 'Running' status found!")
        print("   This is why no active trades are showing in the dashboard")
    
    # 6. Check for common issues
    print(f"\n6. Common issues check:")
    
    # Check for case sensitivity
    case_sensitive_issues = [t for t in trades_after if t.get('status') in ['running', 'RUNNING', 'Run']]
    if case_sensitive_issues:
        print(f"   ⚠️  Found {len(case_sensitive_issues)} trades with incorrect status case")
        for trade in case_sensitive_issues:
            print(f"     - {trade['id']}: '{trade.get('status')}'")
    
    # Check for missing status
    missing_status = [t for t in trades_after if 'status' not in t or t.get('status') is None]
    if missing_status:
        print(f"   ⚠️  Found {len(missing_status)} trades without status")
    
    print(f"\n{'='*50}")
    print("Investigation complete!")
    
    if running_trades:
        print("✅ Everything looks good - active trades should be visible")
    else:
        print("❌ Issue found: No trades have 'Running' status")
        print("💡 Solution: Check why trades are not getting 'Running' status when added")

if __name__ == "__main__":
    investigate_portfolio_issue()
