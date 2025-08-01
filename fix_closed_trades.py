#!/usr/bin/env python
"""
Data Migration Script - Fix Closed Trades Missing Data
This script fixes existing closed trades that don't have final_pnl or closed_date fields
"""
import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils

def fix_closed_trades_data():
    print("=== Fixing Closed Trades Data ===")
    
    # Load all trades
    all_trades = utils.load_trades()
    if not all_trades:
        print("No trades found.")
        return
    
    # Find closed trades
    closed_trades = [t for t in all_trades if t.get('status') in ['Target', 'Stoploss', 'Manually Closed']]
    print(f"Found {len(closed_trades)} closed trades")
    
    fixed_count = 0
    
    for trade in closed_trades:
        updated = False
        trade_id = trade.get('id', 'Unknown')
        
        # Fix missing closed_date
        if 'closed_date' not in trade or not trade['closed_date']:
            trade['closed_date'] = datetime.now().isoformat()
            print(f"  Fixed closed_date for trade {trade_id}")
            updated = True
        
        # Fix missing final_pnl
        if 'final_pnl' not in trade or trade['final_pnl'] is None:
            # Use current pnl if available
            if 'pnl' in trade and trade['pnl'] is not None:
                trade['final_pnl'] = trade['pnl']
                print(f"  Set final_pnl to current pnl ({trade['pnl']}) for trade {trade_id}")
            else:
                # Estimate based on status
                if trade.get('status') == 'Target':
                    target_amount = trade.get('target_amount', 0)
                    trade['final_pnl'] = target_amount
                    print(f"  Estimated final_pnl as target amount ({target_amount}) for trade {trade_id}")
                elif trade.get('status') == 'Stoploss':
                    stoploss_amount = trade.get('stoploss_amount', 0)
                    trade['final_pnl'] = -stoploss_amount
                    print(f"  Estimated final_pnl as negative stoploss ({-stoploss_amount}) for trade {trade_id}")
                else:
                    trade['final_pnl'] = 0
                    print(f"  Set final_pnl to 0 for manually closed trade {trade_id}")
            updated = True
        
        if updated:
            fixed_count += 1
    
    if fixed_count > 0:
        # Save the updated trades
        utils.save_trades(all_trades)
        print(f"\n✅ Fixed {fixed_count} closed trades")
        print("✅ Data saved successfully!")
        
        # Send notification
        utils.send_telegram_message(f"📊 Data Migration Complete: Fixed {fixed_count} closed trades with missing P&L/date data")
    else:
        print("\n✅ All closed trades already have correct data")
    
    print("\n=== Summary ===")
    for trade in closed_trades:
        trade_id = trade.get('id', 'Unknown')
        final_pnl = trade.get('final_pnl', 'Missing')
        closed_date = trade.get('closed_date', 'Missing')
        status = trade.get('status', 'Unknown')
        print(f"  {trade_id}: Status={status}, Final P&L=₹{final_pnl}, Closed Date={closed_date}")

if __name__ == "__main__":
    fix_closed_trades_data()
