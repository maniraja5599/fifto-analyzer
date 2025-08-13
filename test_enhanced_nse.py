#!/usr/bin/env python3
"""
Test Enhanced NSE Integration
============================

Quick test to verify the enhanced NSE provider is working.
"""

import os
import sys
import django
import time

# Add the project path
project_path = '/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer'
sys.path.insert(0, project_path)
os.chdir(project_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

def test_enhanced_nse():
    """Test the enhanced NSE provider"""
    print("🧪 Testing Enhanced NSE Provider")
    print("=" * 50)
    
    try:
        from analyzer.nse_enhanced import get_enhanced_nse_data
        
        print("📡 Fetching enhanced NSE data...")
        start_time = time.time()
        
        data = get_enhanced_nse_data()
        
        elapsed = time.time() - start_time
        print(f"⏱️ Request completed in {elapsed:.2f} seconds")
        
        if data:
            print("✅ Enhanced NSE data received:")
            
            for symbol, info in data.items():
                print(f"\n📊 {symbol}:")
                print(f"   Price: ₹{info.get('price', 'N/A')}")
                print(f"   Change: {info.get('change', 'N/A')} ({info.get('change_percent', 'N/A')}%)")
                print(f"   Source: {info.get('source', 'Unknown')}")
                print(f"   Endpoint: {info.get('endpoint', 'Unknown')}")
                print(f"   Updated: {info.get('last_updated', 'Unknown')}")
        else:
            print("❌ No data received from enhanced NSE provider")
            
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
    except Exception as e:
        print(f"❌ Test error: {str(e)}")

def test_enhanced_market_data():
    """Test the enhanced market data with new NSE provider"""
    print("\n\n🚀 Testing Enhanced Market Data with New NSE")
    print("=" * 50)
    
    try:
        from analyzer.market_data_enhanced import get_enhanced_market_data, get_available_data_sources
        
        print("📋 Available sources:")
        sources = get_available_data_sources()
        for i, source in enumerate(sources, 1):
            print(f"   {i}. {source}")
        
        print("\n🔄 Testing automatic failover...")
        start_time = time.time()
        
        data = get_enhanced_market_data()
        
        elapsed = time.time() - start_time
        print(f"⏱️ Failover completed in {elapsed:.2f} seconds")
        
        if data:
            print("✅ Enhanced market data received:")
            
            for symbol in ['NIFTY', 'BANKNIFTY']:
                if symbol in data:
                    info = data[symbol]
                    print(f"\n📈 {symbol}:")
                    print(f"   Price: ₹{info.get('price', 'N/A')}")
                    print(f"   Change: {info.get('change', 'N/A')} ({info.get('change_percent', 'N/A')}%)")
                    print(f"   Data Source: {info.get('data_source', info.get('source', 'Unknown'))}")
                    print(f"   Fetch Time: {info.get('fetch_time', info.get('last_updated', 'Unknown'))}")
        else:
            print("❌ No data received from enhanced market data")
            
    except Exception as e:
        print(f"❌ Enhanced market data error: {str(e)}")

def test_forced_enhanced_nse():
    """Test forcing the enhanced NSE source"""
    print("\n\n🎯 Testing Forced Enhanced NSE Source")
    print("=" * 50)
    
    try:
        from analyzer.market_data_enhanced import get_enhanced_market_data
        
        print("🔍 Forcing NSE_Enhanced source...")
        data = get_enhanced_market_data(force_source='NSE_Enhanced')
        
        if data:
            print("✅ Forced NSE_Enhanced data:")
            
            for symbol in ['NIFTY', 'BANKNIFTY']:
                if symbol in data:
                    info = data[symbol]
                    source = info.get('data_source', info.get('source', 'Unknown'))
                    print(f"   {symbol}: ₹{info.get('price', 'N/A')} (Source: {source})")
        else:
            print("❌ Failed to get forced NSE_Enhanced data")
            
    except Exception as e:
        print(f"❌ Forced source error: {str(e)}")

if __name__ == "__main__":
    print("🔬 Enhanced NSE Integration Test")
    print("=" * 60)
    print(f"🕒 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_enhanced_nse()
    test_enhanced_market_data()
    test_forced_enhanced_nse()
    
    print("\n\n📋 Summary")
    print("=" * 60)
    print("Enhanced NSE provider includes:")
    print("✅ Proper authentication handling")
    print("✅ GZIP compression support")
    print("✅ Multiple endpoint fallbacks")
    print("✅ Enhanced error handling and retries")
    print("✅ Rate limiting with jitter")
    print("✅ Cookie management and refresh")
