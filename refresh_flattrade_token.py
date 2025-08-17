#!/usr/bin/env python3
"""
FlatTrade Token Refresh Utility

This script helps refresh expired FlatTrade access tokens by guiding through the OAuth flow.
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta

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

def save_settings(settings):
    """Save updated settings"""
    try:
        with open('fifto_settings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        print(f"❌ Error saving settings: {e}")
        return False

def refresh_flattrade_token():
    """Guide through FlatTrade token refresh process"""
    
    print("=" * 60)
    print("FlatTrade Token Refresh Utility")
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
        return False
    
    print(f"📋 Found FlatTrade account: {flattrade_account.get('account_name', 'Unknown')}")
    print(f"🔑 Current API Key: {flattrade_account.get('api_key', 'Not found')}")
    print(f"🔐 Current Client ID: {flattrade_account.get('client_id', 'Not found')}")
    
    current_token = flattrade_account.get('access_token', '')
    token_expiry = flattrade_account.get('token_expiry', '')
    
    print(f"🎫 Current Token: {current_token[:20]}..." if current_token else "🎫 No current token")
    print(f"⏰ Token Expiry: {token_expiry}")
    
    # Test current token
    print("\n🔍 Testing current token...")
    try:
        api = FlatTradeAPI(
            api_key=flattrade_account.get('api_key', ''),
            api_secret=flattrade_account.get('secret_key', ''),
            client_id=flattrade_account.get('client_id', '')
        )
        
        if current_token:
            api.set_access_token(current_token)
            success, result = api.get_user_details()
            
            if success:
                print("✅ Current token is valid!")
                print(f"👤 User: {result.get('uname', 'Unknown')}")
                print(f"🏦 Broker: {result.get('brkname', 'FlatTrade')}")
                return True
            else:
                print(f"❌ Current token is invalid: {result.get('error', 'Unknown error')}")
        else:
            print("❌ No current token found")
    except Exception as e:
        print(f"❌ Error testing token: {e}")
    
    # Generate OAuth URL
    print("\n🔗 Generating OAuth URL...")
    try:
        api_key = flattrade_account.get('api_key', '')
        if not api_key:
            print("❌ API Key not found in settings")
            return False
        
        # Use a redirect URI (this should match what's configured in FlatTrade app)
        redirect_uri = "http://localhost:8080/callback"  # You can change this
        
        oauth_url = FlatTradeAPI.generate_oauth_url(
            api_key=api_key,
            redirect_uri=redirect_uri,
            state="auth_request"
        )
        
        print(f"✅ OAuth URL generated:")
        print(f"🌐 {oauth_url}")
        print()
        print("📋 Next Steps:")
        print("1. Copy the URL above and open it in your browser")
        print("2. Log in to your FlatTrade account")
        print("3. Authorize the application")
        print("4. Copy the 'code' parameter from the callback URL")
        print("5. Come back here and paste the code")
        print()
        
        # Get authorization code from user
        auth_code = input("📥 Enter the authorization code from the callback URL: ").strip()
        
        if not auth_code:
            print("❌ No authorization code provided")
            return False
        
        print(f"🔑 Received authorization code: {auth_code[:10]}...")
        
        # Exchange code for access token
        print("\n🔄 Exchanging code for access token...")
        
        success, token_result = api.exchange_code_for_token(
            code=auth_code,
            api_secret=flattrade_account.get('secret_key', ''),
            redirect_uri=redirect_uri
        )
        
        if success and token_result.get('access_token'):
            new_token = token_result['access_token']
            
            # Calculate expiry time (FlatTrade tokens typically expire in 24 hours)
            expiry_time = datetime.now() + timedelta(hours=24)
            expiry_str = expiry_time.isoformat()
            
            print(f"✅ New access token received: {new_token[:20]}...")
            print(f"⏰ Token expires: {expiry_str}")
            
            # Update settings
            flattrade_account['access_token'] = new_token
            flattrade_account['token_expiry'] = expiry_str
            
            if save_settings(settings):
                print("✅ Settings updated successfully!")
                
                # Test new token
                print("\n🔍 Testing new token...")
                api.set_access_token(new_token)
                success, result = api.get_user_details()
                
                if success:
                    print("✅ New token is working!")
                    print(f"👤 User: {result.get('uname', 'Unknown')}")
                    print(f"🏦 Broker: {result.get('brkname', 'FlatTrade')}")
                    print("\n🎉 Token refresh completed successfully!")
                    return True
                else:
                    print(f"❌ New token test failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print("❌ Failed to save updated settings")
                return False
        else:
            print(f"❌ Failed to get access token: {token_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error during token refresh: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        if refresh_flattrade_token():
            print("\n" + "=" * 60)
            print("✅ FlatTrade token refresh completed successfully!")
            print("You can now try running your automation again.")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ FlatTrade token refresh failed.")
            print("Please check the errors above and try again.")
            print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n❌ Token refresh cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
