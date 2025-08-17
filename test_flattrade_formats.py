#!/usr/bin/env python3
"""
FlatTrade API Format Tester

This script tests different ways to format the FlatTrade API request to find what works.
"""

import sys
import os
import json
import logging
import requests
from urllib.parse import quote, urlencode

# Add project root to path
sys.path.append('/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer')

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

def test_flattrade_formats():
    """Test different request formats for FlatTrade API"""
    
    print("=" * 80)
    print("FlatTrade API Format Tester")
    print("=" * 80)
    
    # Load settings
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
    
    api_key = flattrade_account.get('api_key', '')
    access_token = flattrade_account.get('access_token', '')
    client_id = flattrade_account.get('client_id', '')
    
    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"🎫 Token: {access_token[:10]}...")
    print(f"👤 Client ID: {client_id}")
    
    # Test data
    test_data = {'uid': client_id}
    url = "https://piconnect.flattrade.in/PiConnectTP/UserDetails"
    
    # Format variations to test
    formats = [
        {
            'name': 'Current URL-encoded format',
            'prepare': lambda data, token: f"jData={quote(json.dumps(data, separators=(',', ':')))}&jKey={quote(token)}",
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'method': 'data'
        },
        {
            'name': 'Simple form data',
            'prepare': lambda data, token: {
                'jData': json.dumps(data, separators=(',', ':')),
                'jKey': token
            },
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'method': 'data'
        },
        {
            'name': 'Form data with urlencode',
            'prepare': lambda data, token: urlencode({
                'jData': json.dumps(data, separators=(',', ':')),
                'jKey': token
            }),
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'method': 'data'
        },
        {
            'name': 'No separators in JSON',
            'prepare': lambda data, token: f"jData={quote(json.dumps(data))}&jKey={quote(token)}",
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'method': 'data'
        },
        {
            'name': 'Raw string without encoding',
            'prepare': lambda data, token: f"jData={json.dumps(data)}&jKey={token}",
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'method': 'data'
        },
        {
            'name': 'JSON body format',
            'prepare': lambda data, token: {
                'jData': json.dumps(data),
                'jKey': token
            },
            'headers': {'Content-Type': 'application/json'},
            'method': 'json'
        },
        {
            'name': 'Nested JSON format',
            'prepare': lambda data, token: {
                'data': data,
                'token': token
            },
            'headers': {'Content-Type': 'application/json'},
            'method': 'json'
        }
    ]
    
    print(f"\n🧪 Testing {len(formats)} different formats...\n")
    
    session = requests.Session()
    
    for i, fmt in enumerate(formats, 1):
        print(f"📝 Test {i}: {fmt['name']}")
        print("-" * 50)
        
        try:
            # Prepare the payload
            payload = fmt['prepare'](test_data, access_token)
            
            print(f"Payload type: {type(payload)}")
            if isinstance(payload, str):
                print(f"Payload: {payload[:100]}{'...' if len(payload) > 100 else ''}")
            else:
                print(f"Payload: {payload}")
            
            # Make the request
            if fmt['method'] == 'json':
                response = session.post(url, json=payload, headers=fmt['headers'], timeout=30)
            else:
                response = session.post(url, data=payload, headers=fmt['headers'], timeout=30)
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
            
            # Try to parse response
            try:
                response_data = response.json()
                if response_data.get('stat') == 'Ok':
                    print("🎉 SUCCESS! This format works!")
                    print(f"✅ User: {response_data.get('uname', 'N/A')}")
                    print(f"✅ Client: {response_data.get('actid', 'N/A')}")
                    return True
                elif 'jData is not valid json object' in response_data.get('emsg', ''):
                    print("❌ JSON validation error")
                elif 'Session Expired' in response_data.get('emsg', ''):
                    print("❌ Authentication error (token expired)")
                else:
                    print(f"❌ API error: {response_data.get('emsg', 'Unknown')}")
            except json.JSONDecodeError:
                print("❌ Non-JSON response")
            
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        print()
    
    print("🔍 All formats tested. None succeeded.")
    print("\n💡 Possible solutions:")
    print("1. Token might be expired - run: python3 refresh_flattrade_token.py")
    print("2. API endpoint might be incorrect")
    print("3. Account configuration might be wrong")
    print("4. API access might not be enabled for your account")
    
    return False

if __name__ == "__main__":
    try:
        if test_flattrade_formats():
            print("\n" + "=" * 80)
            print("✅ Found working format!")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ No working format found.")
            print("=" * 80)
    except KeyboardInterrupt:
        print("\n\n❌ Testing cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
