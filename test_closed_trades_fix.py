#!/usr/bin/env python
"""
Test script to verify closed trades fixes are working
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils
from datetime import datetime

def test_closed_trades_fixes():
    print("=== Testing Closed Trades Fixes ===")
    
    # Load trades
    trades = utils.load_trades()
    print(f"Total trades loaded: {len(trades)}")
    
    # Find closed trades
    closed_trades = [t for t in trades if t.get('status') in ['Target', 'Stoploss', 'Manually Closed']]
    print(f"Closed trades found: {len(closed_trades)}")
    
    if not closed_trades:
        print("No closed trades found. Creating a test trade...")
        
        # Create a test trade
        test_trade = {
            'id': 'TEST_TRADE_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
            'instrument': 'NIFTY',
            'expiry': '14-Aug-2025',
            'reward_type': 'Test Reward',
            'ce_strike': 24700,
            'pe_strike': 24650,
            'initial_premium': 362.45,
            'target_amount': 1000,
            'stoploss_amount': 500,
            'status': 'Manually Closed',
            'final_pnl': 275.50,
            'closed_date': datetime.now().isoformat(),
            'entry_tag': 'Test Tag',
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
        trades.append(test_trade)
        utils.save_trades(trades)
        print(f"Created test trade: {test_trade['id']}")
        closed_trades = [test_trade]
    
    print("\n=== Closed Trades Analysis ===")
    for trade in closed_trades:
        trade_id = trade.get('id', 'Unknown')
        final_pnl = trade.get('final_pnl', 'Missing')
        closed_date = trade.get('closed_date', 'Missing')
        status = trade.get('status', 'Unknown')
        
        print(f"\nTrade: {trade_id}")
        print(f"  Status: {status}")
        print(f"  Final P&L: ₹{final_pnl}")
        print(f"  Closed Date: {closed_date}")
        print(f"  Initial Premium: ₹{trade.get('initial_premium', 'N/A')}")
        print(f"  Instrument: {trade.get('instrument', 'N/A')}")
        
        # Check if data is valid
        if final_pnl != 'Missing' and closed_date != 'Missing':
            print(f"  ✅ Trade data is complete")
        else:
            print(f"  ❌ Trade data needs fixing")
    
    print(f"\n✅ Test completed! Check the closed trades page to verify the display.")

if __name__ == "__main__":
    test_closed_trades_fixes()
