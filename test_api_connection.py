#!/usr/bin/env python3
"""
Quick API Connection Test

Tests the current FlatTrade API connection with the saved token.
"""

import sys
import os
import json
import requests

# Add project root to path
sys.path.append('/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer')

def test_api_connection():
    """Test FlatTrade API connection"""
    
    print("=" * 60)
    print("🔗 FlatTrade API Connection Test")
    print("=" * 60)
    
    try:
        # Load Django settings
        settings_file = os.path.expanduser('~/app_settings.json')
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            print("✅ Loaded Django settings")
        else:
            print("❌ Django settings not found, using project settings")
            with open('fifto_settings.json', 'r') as f:
                settings = json.load(f)
        
        # Find FlatTrade account
        flattrade_account = None
        for account in settings.get('broker_accounts', []):
            if account.get('broker') == 'FLATTRADE':
                flattrade_account = account
                break
        
        if not flattrade_account:
            print("❌ No FlatTrade account found")
            return False
        
        client_id = flattrade_account.get('client_id', '')
        access_token = flattrade_account.get('access_token', '')
        
        print(f"👤 Client ID: {client_id}")
        print(f"🎫 Token: {access_token[:10] if access_token else 'None'}...")
        
        if not access_token:
            print("❌ No access token found")
            return False
        
        # Test API call
        url = "https://piconnect.flattrade.in/PiConnectTP/UserDetails"
        payload = f"jData={{\"uid\":\"{client_id}\"}}&jKey={access_token}"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        print(f"\n🧪 Testing API call...")
        print(f"URL: {url}")
        print(f"Payload length: {len(payload)} chars")
        
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('stat') == 'Ok':
                    print("\n🎉 API Connection Successful!")
                    print(f"✅ User: {data.get('uname', 'N/A')}")
                    print(f"✅ Client: {data.get('actid', 'N/A')}")
                    print(f"✅ Mobile: {data.get('m_num', 'N/A')}")
                    return True
                else:
                    print(f"\n❌ API Error: {data.get('emsg', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                print("\n❌ Invalid JSON response")
                return False
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    if test_api_connection():
        print("\n" + "=" * 60)
        print("✅ FlatTrade connection is working properly!")
        print("You can now use the broker for live trading.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ FlatTrade connection failed.")
        print("Please check your OAuth authentication.")
        print("=" * 60)
