#!/usr/bin/env python
"""Debug script to check broker_manager state"""

import os
import sys
import django

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

try:
    print("🔍 Importing broker_manager...")
    from analyzer.broker_manager import broker_manager
    
    print(f"🔍 Broker Manager Type: {type(broker_manager)}")
    print(f"🔍 Active Accounts: {len(broker_manager.active_accounts)}")
    print(f"🔍 Brokers Initialized: {len(broker_manager.brokers)}")
    print(f"🔍 Broker Keys: {list(broker_manager.brokers.keys())}")
    
    # Check each active account
    for i, account in enumerate(broker_manager.active_accounts):
        print(f"🔍 Account {i+1}: {account.get('broker')} - {account.get('client_id', account.get('account_id'))} - Enabled: {account.get('enabled')}")
    
    # Try to reload accounts
    print("\n🔄 Reloading broker accounts...")
    broker_manager.load_broker_accounts()
    
    print(f"🔍 After Reload - Active Accounts: {len(broker_manager.active_accounts)}")
    print(f"🔍 After Reload - Brokers: {len(broker_manager.brokers)}")
    print(f"🔍 After Reload - Broker Keys: {list(broker_manager.brokers.keys())}")
    
    # Test placing orders with a simple test data
    print("\n🧪 Testing place_strategy_orders...")
    test_data = {
        'instrument': 'NIFTY',
        'strikes': {
            'ce_strike': {'symbol': 'NIFTY2312525000CE', 'ltp': 100},
            'pe_strike': {'symbol': 'NIFTY2312525000PE', 'ltp': 150}
        },
        'hedge': {
            'ce_buy_hedge': {'symbol': 'NIFTY2312526000CE', 'ltp': 50},
            'pe_buy_hedge': {'symbol': 'NIFTY2312524000PE', 'ltp': 80}
        }
    }
    
    result = broker_manager.place_strategy_orders(test_data)
    print(f"🔍 Test Result: {result}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
