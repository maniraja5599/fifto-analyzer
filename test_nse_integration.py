#!/usr/bin/env python
"""
Test NSE Data Integration
========================

This script tests the new NSE data integration and multi-source market data fetching.
It will test all available data sources and show which ones are working.
"""

import os
import sys
import django

# Add the project path
project_path = '/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer'
sys.path.insert(0, project_path)
os.chdir(project_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from datetime import datetime
import json

def test_nse_data_sources():
    """Test all NSE data sources"""
    print("🧪 Testing NSE Data Sources")
    print("=" * 50)
    
    # Test NSE direct API
    print("\n1️⃣ Testing NSE Direct API")
    try:
        from analyzer.nse_data import get_nse_market_data
        nse_data = get_nse_market_data()
        
        if nse_data:
            print("✅ NSE Direct API - SUCCESS")
            print(f"   NIFTY: ₹{nse_data.get('NIFTY', {}).get('price', 'N/A')}")
            print(f"   BANKNIFTY: ₹{nse_data.get('BANKNIFTY', {}).get('price', 'N/A')}")
            print(f"   Source: {nse_data.get('NIFTY', {}).get('source', 'Unknown')}")
        else:
            print("❌ NSE Direct API - FAILED")
    except Exception as e:
        print(f"❌ NSE Direct API - ERROR: {str(e)}")
    
    # Test alternative NSE (Yahoo Finance)
    print("\n2️⃣ Testing NSE Alternative (Yahoo Finance)")
    try:
        from analyzer.nse_data import get_alternative_nse_data
        alt_data = get_alternative_nse_data()
        
        if alt_data:
            print("✅ NSE Alternative API - SUCCESS")
            print(f"   NIFTY: ₹{alt_data.get('NIFTY', {}).get('price', 'N/A')}")
            print(f"   BANKNIFTY: ₹{alt_data.get('BANKNIFTY', {}).get('price', 'N/A')}")
            print(f"   Source: {alt_data.get('NIFTY', {}).get('source', 'Unknown')}")
        else:
            print("❌ NSE Alternative API - FAILED")
    except Exception as e:
        print(f"❌ NSE Alternative API - ERROR: {str(e)}")

def test_enhanced_market_data():
    """Test enhanced market data with multi-source support"""
    print("\n\n🚀 Testing Enhanced Market Data")
    print("=" * 50)
    
    try:
        from analyzer.market_data_enhanced import get_enhanced_market_data, test_data_sources, get_available_data_sources
        
        # Test available sources
        print("\n📋 Available Data Sources:")
        sources = get_available_data_sources()
        for i, source in enumerate(sources, 1):
            print(f"   {i}. {source}")
        
        # Test all sources
        print("\n🧪 Testing All Sources:")
        test_results = test_data_sources()
        
        for source, result in test_results.items():
            status = result.get('status', 'unknown')
            if status == 'success':
                nifty_price = result.get('nifty_price', 'N/A')
                banknifty_price = result.get('banknifty_price', 'N/A')
                print(f"   ✅ {source}: NIFTY=₹{nifty_price}, BANKNIFTY=₹{banknifty_price}")
            elif status == 'invalid_data':
                print(f"   ⚠️ {source}: Invalid data returned")
            else:
                error = result.get('error', 'Unknown error')
                print(f"   ❌ {source}: {error}")
        
        # Test automatic fallover
        print("\n🔄 Testing Automatic Failover:")
        market_data = get_enhanced_market_data()
        
        if market_data:
            print("✅ Enhanced Market Data - SUCCESS")
            nifty_data = market_data.get('NIFTY', {})
            banknifty_data = market_data.get('BANKNIFTY', {})
            
            print(f"   NIFTY: ₹{nifty_data.get('price', 'N/A')} ({nifty_data.get('change_percent', 'N/A')}%)")
            print(f"   Source: {nifty_data.get('source', 'Unknown')}")
            print(f"   Updated: {nifty_data.get('last_updated', 'Unknown')}")
            
            print(f"   BANKNIFTY: ₹{banknifty_data.get('price', 'N/A')} ({banknifty_data.get('change_percent', 'N/A')}%)")
            print(f"   Source: {banknifty_data.get('source', 'Unknown')}")
            print(f"   Updated: {banknifty_data.get('last_updated', 'Unknown')}")
        else:
            print("❌ Enhanced Market Data - FAILED")
            
    except Exception as e:
        print(f"❌ Enhanced Market Data - ERROR: {str(e)}")

def test_forced_sources():
    """Test forcing specific data sources"""
    print("\n\n🎯 Testing Forced Data Sources")
    print("=" * 50)
    
    try:
        from analyzer.market_data_enhanced import get_enhanced_market_data
        
        sources_to_test = ['NSE_Direct', 'NSE_Yahoo', 'Fallback']
        
        for source in sources_to_test:
            print(f"\n🔍 Testing forced source: {source}")
            try:
                data = get_enhanced_market_data(force_source=source)
                if data:
                    nifty_data = data.get('NIFTY', {})
                    print(f"   ✅ {source}: NIFTY=₹{nifty_data.get('price', 'N/A')} ({nifty_data.get('source', 'Unknown')})")
                else:
                    print(f"   ❌ {source}: No data returned")
            except Exception as e:
                print(f"   ❌ {source}: {str(e)}")
                
    except Exception as e:
        print(f"❌ Forced Sources Test - ERROR: {str(e)}")

def test_api_endpoints():
    """Test the new API endpoints"""
    print("\n\n🌐 Testing API Endpoints")
    print("=" * 50)
    
    try:
        import requests
        base_url = "http://127.0.0.1:8000"
        
        # Test enhanced market data API
        print("\n📡 Testing Enhanced Market Data API")
        try:
            response = requests.get(f"{base_url}/api/enhanced-market-data/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print("✅ Enhanced Market Data API - SUCCESS")
                print(f"   NIFTY: ₹{data['market_data']['NIFTY']['current_price']}")
                print(f"   Source: {data['market_data']['NIFTY']['source']}")
            else:
                print(f"❌ Enhanced Market Data API - HTTP {response.status_code}")
        except Exception as e:
            print(f"⚠️ Enhanced Market Data API - Server not running: {str(e)}")
        
        # Test data sources test API
        print("\n🧪 Testing Data Sources Test API")
        try:
            response = requests.get(f"{base_url}/api/test-data-sources/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print("✅ Data Sources Test API - SUCCESS")
                test_results = data.get('test_results', {})
                for source, result in test_results.items():
                    status = result.get('status', 'unknown')
                    print(f"   {source}: {status}")
            else:
                print(f"❌ Data Sources Test API - HTTP {response.status_code}")
        except Exception as e:
            print(f"⚠️ Data Sources Test API - Server not running: {str(e)}")
            
    except Exception as e:
        print(f"❌ API Endpoints Test - ERROR: {str(e)}")

def main():
    """Main test function"""
    print("🔬 NSE Data Integration Test Suite")
    print("=" * 60)
    print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Project Path: {project_path}")
    
    # Run all tests
    test_nse_data_sources()
    test_enhanced_market_data()
    test_forced_sources()
    test_api_endpoints()
    
    print("\n\n✨ Test Suite Complete!")
    print("=" * 60)
    print("📊 Summary:")
    print("   - NSE Direct API integration added")
    print("   - NSE Yahoo Finance fallback added") 
    print("   - Enhanced market data with multi-source support")
    print("   - New API endpoints for enhanced data")
    print("   - Automatic failover between sources")
    print("\n💡 Usage:")
    print("   - Use /api/enhanced-market-data/ for multi-source data")
    print("   - Add ?source=NSE_Direct to force NSE direct")
    print("   - Add ?source=NSE_Yahoo to force Yahoo Finance NSE")
    print("   - Use /api/test-data-sources/ to test all sources")

if __name__ == "__main__":
    main()
