#!/usr/bin/env python3
"""
NSE API Debug Script
===================

This script tests the NSE API directly to understand authentication issues.
"""

import requests
import json
import time
from datetime import datetime

def test_nse_direct():
    """Test NSE API directly"""
    print("🔍 Testing NSE Direct API")
    print("=" * 50)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    base_url = "https://www.nseindia.com"
    
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {base_url}")
    
    # Step 1: Get cookies from NSE homepage
    print("\n1️⃣ Getting cookies from NSE homepage...")
    try:
        homepage_response = session.get(base_url, timeout=15)
        print(f"   Status: {homepage_response.status_code}")
        print(f"   Cookies: {len(session.cookies)} cookies received")
        
        for cookie in session.cookies:
            cookie_value = str(cookie.value) if cookie.value else "None"
            print(f"   Cookie: {cookie.name} = {cookie_value[:20]}...")
            
    except Exception as e:
        print(f"   ❌ Error getting homepage: {str(e)}")
        return
    
    # Step 2: Test allIndices API
    print("\n2️⃣ Testing allIndices API...")
    try:
        time.sleep(2)  # Rate limiting
        api_url = f"{base_url}/api/allIndices"
        
        print(f"   URL: {api_url}")
        print(f"   Headers: {dict(session.headers)}")
        
        api_response = session.get(api_url, timeout=15)
        print(f"   Status: {api_response.status_code}")
        print(f"   Content-Type: {api_response.headers.get('content-type', 'unknown')}")
        print(f"   Response length: {len(api_response.text)} chars")
        
        if api_response.status_code == 200:
            try:
                data = api_response.json()
                print(f"   ✅ JSON response received")
                print(f"   Keys in response: {list(data.keys())}")
                
                if 'data' in data:
                    indices = data['data']
                    print(f"   Found {len(indices)} indices")
                    
                    # Look for NIFTY and BANKNIFTY
                    found_indices = []
                    for index in indices[:10]:  # Check first 10
                        index_name = index.get('index', 'Unknown')
                        last_price = index.get('last', 'N/A')
                        found_indices.append(f"{index_name}: {last_price}")
                        
                        if 'NIFTY' in index_name:
                            print(f"   🎯 Found: {index_name} = {last_price}")
                    
                    print(f"   Sample indices: {found_indices[:5]}")
                else:
                    print(f"   ⚠️ No 'data' key in response")
                    print(f"   Response preview: {str(data)[:200]}...")
                    
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {str(e)}")
                print(f"   Response preview: {api_response.text[:500]}...")
        else:
            print(f"   ❌ API Error: {api_response.status_code}")
            print(f"   Response headers: {dict(api_response.headers)}")
            print(f"   Response preview: {api_response.text[:500]}...")
            
    except Exception as e:
        print(f"   ❌ Error calling API: {str(e)}")

def test_alternative_nse_endpoints():
    """Test alternative NSE endpoints"""
    print("\n\n🔧 Testing Alternative NSE Endpoints")
    print("=" * 50)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/',
        'sec-ch-ua': '"Chromium";v="91", " Not;A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
    })
    
    # Get cookies first
    print("Getting cookies...")
    try:
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(2)
    except:
        pass
    
    endpoints_to_test = [
        "/api/allIndices",
        "/api/equity-stockIndices?index=NIFTY%2050", 
        "/api/equity-stockIndices?index=NIFTY%20BANK",
        "/api/chart-databyindex?index=NIFTY%2050&indices=true",
        "/api/chart-databyindex?index=NIFTY%20BANK&indices=true"
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\n🔍 Testing: {endpoint}")
        try:
            url = f"https://www.nseindia.com{endpoint}"
            response = session.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Success - Keys: {list(data.keys())}")
                    
                    # Look for price data
                    if 'data' in data and isinstance(data['data'], list):
                        for item in data['data'][:2]:
                            if isinstance(item, dict):
                                name = item.get('index', item.get('symbol', 'Unknown'))
                                price = item.get('last', item.get('lastPrice', 'N/A'))
                                print(f"      {name}: {price}")
                    elif 'grapthData' in data:
                        graph_data = data['grapthData']
                        if graph_data:
                            latest = graph_data[-1]
                            print(f"      Latest: {latest}")
                            
                except json.JSONDecodeError:
                    print(f"   ⚠️ Not JSON - Content preview: {response.text[:100]}...")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        time.sleep(1)  # Rate limiting

def test_public_nse_apis():
    """Test publicly available NSE APIs"""
    print("\n\n🌐 Testing Public NSE APIs")
    print("=" * 50)
    
    # Test some known working NSE endpoints
    public_apis = [
        {
            'name': 'NSE Holiday Calendar',
            'url': 'https://www.nseindia.com/api/holiday-master?type=trading'
        },
        {
            'name': 'NSE Market Status',
            'url': 'https://www.nseindia.com/api/marketStatus'
        },
        {
            'name': 'NSE Live Indices (simple)',
            'url': 'https://www.nseindia.com/api/allIndices'
        }
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
    })
    
    # Get initial cookies
    try:
        print("🍪 Getting cookies from NSE homepage...")
        homepage = session.get("https://www.nseindia.com", timeout=10)
        print(f"   Homepage status: {homepage.status_code}")
        print(f"   Cookies received: {len(session.cookies)}")
        time.sleep(3)  # Wait a bit
    except Exception as e:
        print(f"   ⚠️ Cookie fetch error: {str(e)}")
    
    for api in public_apis:
        print(f"\n🧪 Testing: {api['name']}")
        try:
            response = session.get(api['url'], timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Success")
                    print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    # Special handling for allIndices
                    if 'allIndices' in api['url'] and 'data' in data:
                        indices_data = data['data']
                        nifty_indices = [idx for idx in indices_data if 'NIFTY' in idx.get('index', '').upper()]
                        print(f"   Found {len(nifty_indices)} NIFTY indices")
                        for idx in nifty_indices[:3]:
                            name = idx.get('index', 'Unknown')
                            price = idx.get('last', 'N/A')
                            change = idx.get('change', 'N/A')
                            print(f"      {name}: ₹{price} ({change})")
                            
                except json.JSONDecodeError as e:
                    print(f"   ⚠️ JSON error: {str(e)}")
                    print(f"   Content preview: {response.text[:200]}...")
            else:
                print(f"   ❌ HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ Request error: {str(e)}")
        
        time.sleep(2)  # Rate limiting

if __name__ == "__main__":
    print("🔬 NSE API Authentication Debug")
    print("=" * 60)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_nse_direct()
    test_alternative_nse_endpoints()
    test_public_nse_apis()
    
    print("\n\n📋 Summary")
    print("=" * 60)
    print("This script tests various NSE API endpoints to identify authentication issues.")
    print("Common issues:")
    print("- NSE requires proper User-Agent headers")
    print("- Some endpoints need cookies from homepage")
    print("- Rate limiting is strictly enforced")
    print("- CORS policies may block certain requests")
    print("- Authentication tokens may be required for some data")
