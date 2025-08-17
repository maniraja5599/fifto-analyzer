#!/usr/bin/env python3
"""
Test FlatTrade API order placement to debug issues
"""

import sys
import os
import logging
import json

# Add the project root to Python path
sys.path.append('/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer')

from analyzer.flattrade_api import FlatTradeBrokerHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_flattrade_connection():
    """Test FlatTrade connection and basic functionality"""
    
    print("=" * 60)
    print("FlatTrade API Test Script")
    print("=" * 60)
    
    # Load broker configuration
    try:
        with open('fifto_settings.json', 'r') as f:
            settings = json.load(f)
        
        broker_accounts = settings.get('broker_accounts', [])
        flattrade_config = None
        
        # Find FlatTrade configuration
        for config in broker_accounts:
            if config.get('broker') == 'FLATTRADE' and config.get('enabled'):
                flattrade_config = config
                print(f"✅ Found FlatTrade config for account: {config.get('account_name', 'Unknown')}")
                break
        
        if not flattrade_config:
            print("❌ No enabled FlatTrade account found in settings")
            return False
            
        # Create FlatTrade handler
        handler = FlatTradeBrokerHandler(flattrade_config)
        
        # Test 1: Connection test
        print("\n🔍 Testing connection...")
        connection_result = handler.test_connection()
        print(f"Connection result: {connection_result}")
        
        if not connection_result.get('success'):
            print("❌ Connection test failed")
            return False
        
        print("✅ Connection successful")
        
        # Test 2: Get user details
        print("\n🔍 Testing user details...")
        success, user_details = handler.api.get_user_details()
        if success:
            print(f"✅ User details: {user_details.get('uname', 'Unknown')}")
        else:
            print(f"❌ User details failed: {user_details}")
            
        # Test 3: Get limits
        print("\n🔍 Testing account limits...")
        success, limits = handler.api.get_limits()
        if success:
            print(f"✅ Account limits retrieved")
        else:
            print(f"❌ Limits failed: {limits}")
            
        # Test 4: Test JSON formatting
        print("\n🔍 Testing JSON formatting...")
        test_data = {
            'uid': handler.api.client_id,
            'actid': handler.api.client_id,
            'exch': 'NFO',
            'tsym': 'NIFTY21AUG25C24650',
            'qty': '75',
            'prc': '0',
            'prd': 'M',
            'trantype': 'B',
            'prctyp': 'MKT',
            'ret': 'DAY',
            'dscqty': '0',
            'ordersource': 'API'
        }
        
        json_str = json.dumps(test_data, separators=(',', ':'), ensure_ascii=False)
        print(f"✅ JSON formatting test: {json_str}")
        
        # Test 5: Symbol generation
        print("\n🔍 Testing symbol generation...")
        try:
            symbol = handler._generate_option_symbol('NIFTY', '21-Aug-2025', 24650, 'CE')
            print(f"✅ Generated symbol: {symbol}")
        except Exception as e:
            print(f"❌ Symbol generation failed: {e}")
            
        print("\n" + "=" * 60)
        print("✅ All tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_flattrade_connection()
