#!/usr/bin/env python3
"""
Quick script to clear existing trades for testing
"""
import os
import sys

# Set up Django
project_dir = r"c:\Users\manir\Desktop\New folder\Django\fifto_project"
sys.path.append(project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

import django
django.setup()

from analyzer import utils

def clear_trades():
    print("🧹 Clearing all existing trades...")
    
    # Load current trades
    trades = utils.load_trades()
    print(f"📊 Found {len(trades)} existing trades")
    
    if trades:
        print("🗑️ Trades to be cleared:")
        for trade in trades:
            print(f"   - {trade.get('id', 'NO_ID')} | {trade.get('status', 'NO_STATUS')}")
    
    # Clear all trades
    utils.save_trades([])
    
    # Verify clearing worked
    trades_after = utils.load_trades()
    print(f"✅ After clearing: {len(trades_after)} trades remain")
    
    if len(trades_after) == 0:
        print("🎉 All trades cleared successfully!")
    else:
        print("❌ Some trades still remain")

if __name__ == "__main__":
    clear_trades()
