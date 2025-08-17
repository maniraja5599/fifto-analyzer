#!/usr/bin/env python3
"""
Quick FlatTrade Token Validator

This script quickly checks if your FlatTrade token is working and provides guidance.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.append('/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer')

from analyzer.flattrade_api import FlatTradeAPI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_settings():
    """Load current settings"""
    try:
        with open('fifto_settings.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return None

def validate_flattrade_token():
    """Validate current FlatTrade token"""
    
    print("=" * 60)
    print("FlatTrade Token Validator")
    print("=" * 60)
    
    # Load current settings
    settings = load_settings()
    if not settings:
        return False
    
    # Find FlatTrade account
    flattrade_account = None
    for account in settings.get('broker_accounts', []):
        if account.get('broker') == 'FLATTRADE':
            flattrade_account = account
            break
    
    if not flattrade_account:
        print("❌ No FlatTrade account found in settings")
        print("\n💡 Solution:")
        print("   1. Add a FlatTrade account in your settings")
        print("   2. Or check if the broker name is correct (should be 'FLATTRADE')")
        return False
    
    print(f"📋 Found FlatTrade account: {flattrade_account.get('account_name', 'Unknown')}")
    
    # Check required fields
    required_fields = ['api_key', 'secret_key', 'client_id', 'access_token']
    missing_fields = []
    
    for field in required_fields:
        value = flattrade_account.get(field, '')
        if not value:
            missing_fields.append(field)
        else:
            print(f"✅ {field}: {'*' * 10}{value[-4:] if len(value) > 4 else value}")
    
    if missing_fields:
        print(f"\n❌ Missing required fields: {', '.join(missing_fields)}")
        print("\n💡 Solution:")
        print("   1. Get these values from your FlatTrade API settings")
        print("   2. Update your fifto_settings.json file")
        print("   3. For access_token, run: python refresh_flattrade_token.py")
        return False
    
    # Test token
    print(f"\n🔍 Testing access token...")
    try:
        api = FlatTradeAPI(
            api_key=flattrade_account.get('api_key', ''),
            api_secret=flattrade_account.get('secret_key', ''),
            client_id=flattrade_account.get('client_id', '')
        )
        
        api.set_access_token(flattrade_account.get('access_token', ''))
        
        # Test the token
        if api.is_token_valid():
            print("✅ FlatTrade token is VALID!")
            
            # Get user details
            success, result = api.get_user_details()
            if success:
                print(f"👤 User: {result.get('uname', 'Unknown')}")
                print(f"🏦 Broker: {result.get('brkname', 'FlatTrade')}")
                print(f"🔢 Client ID: {result.get('actid', 'Unknown')}")
                
                # Test a simple quote (using NIFTY token)
                print(f"\n🔍 Testing market data access...")
                success, quotes = api.get_quotes('NSE', '26000')  # NIFTY INDEX token
                if success:
                    print("✅ Market data access working!")
                    if quotes:
                        print(f"📈 NIFTY data received: {str(quotes)[:100]}...")
                else:
                    print(f"⚠️  Market data test failed: {quotes.get('error', 'Unknown error')}")
                    print("   (This is normal - market data access requires different permissions)")
                
                print(f"\n🎉 FlatTrade integration is working correctly!")
                print(f"   You can now use automation features with FlatTrade.")
                return True
            else:
                print(f"❌ Failed to get user details: {result.get('error', 'Unknown error')}")
                return False
        else:
            print("❌ FlatTrade token is INVALID or EXPIRED!")
            
            # Get more specific error info
            success, result = api.get_user_details()
            error_msg = result.get('error', 'Unknown error')
            print(f"   Error: {error_msg}")
            
            if result.get('auth_error'):
                print("\n💡 This is an authentication error. Your token needs to be refreshed.")
                print("   Run: python refresh_flattrade_token.py")
            else:
                print(f"\n💡 Specific error: {error_msg}")
                print("   This might be a configuration or network issue.")
            
            return False
            
    except Exception as e:
        print(f"❌ Error testing token: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        if validate_flattrade_token():
            print("\n" + "=" * 60)
            print("✅ FlatTrade validation completed successfully!")
            print("Your automation system is ready to use.")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ FlatTrade validation failed.")
            print("Please follow the solutions above to fix the issues.")
            print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n❌ Validation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
