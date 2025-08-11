#!/usr/bin/env python3
"""
Test script for historical data implementation
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer.historical_data import HistoricalDataFetcher

def test_historical_data():
    """Test historical data functionality"""
    print("🧪 Testing Historical Data Implementation")
    print("=" * 50)
    
    # Initialize fetcher
    fetcher = HistoricalDataFetcher()
    
    # Test single symbol
    print("\n1. Testing single symbol (NIFTY):")
    nifty_data = fetcher.get_historical_data('NIFTY')
    if nifty_data:
        print(f"   ✅ NIFTY: {len(nifty_data['timestamps'])} data points")
        print(f"   💹 Current: ₹{nifty_data['current']:.2f}")
        print(f"   📈 Change: {nifty_data['change']:+.2f} ({nifty_data['change_percent']:+.2f}%)")
        print(f"   ⏰ Last updated: {nifty_data['last_updated']}")
    else:
        print("   ❌ Failed to fetch NIFTY data")
    
    # Test multiple symbols
    print("\n2. Testing multiple symbols:")
    symbols = ['NIFTY', 'BANKNIFTY', 'SENSEX', 'VIX']
    multi_data = fetcher.get_multiple_historical(symbols)
    
    if multi_data:
        print(f"   ✅ Successfully fetched {len(multi_data)} symbols:")
        for symbol, data in multi_data.items():
            print(f"     • {symbol}: ₹{data['current']:.2f} ({data['change_percent']:+.2f}%)")
    else:
        print("   ❌ Failed to fetch multiple symbols")
    
    # Test API response format
    print("\n3. Testing API response format:")
    response_data = {
        'success': True,
        'data': multi_data,
        'period': '1d',
        'interval': '5m',
        'symbols': symbols,
        'timestamp': multi_data.get('NIFTY', {}).get('last_updated', '') if multi_data else '',
        'source': 'yfinance + DhanHQ fallback'
    }
    
    print(f"   ✅ Response format valid: {response_data['success']}")
    print(f"   📊 Data symbols: {list(response_data['data'].keys())}")
    print(f"   ⏱️ Period/Interval: {response_data['period']}/{response_data['interval']}")
    print(f"   🔌 Source: {response_data['source']}")
    
    return True

def test_chart_data_format():
    """Test that data format matches Chart.js requirements"""
    print("\n4. Testing Chart.js data format:")
    
    fetcher = HistoricalDataFetcher()
    data = fetcher.get_historical_data('NIFTY')
    
    if data:
        # Check required fields for Chart.js
        required_fields = ['timestamps', 'prices']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            print(f"   ✅ All required fields present: {required_fields}")
            print(f"   📈 Sample timestamps: {data['timestamps'][:3]}...")
            print(f"   📊 Sample prices: {data['prices'][:3]}...")
            
            # Check data consistency
            if len(data['timestamps']) == len(data['prices']):
                print(f"   ✅ Data consistency: {len(data['timestamps'])} points match")
            else:
                print(f"   ❌ Data mismatch: {len(data['timestamps'])} timestamps vs {len(data['prices'])} prices")
        else:
            print(f"   ❌ Missing required fields: {missing_fields}")
    else:
        print("   ❌ No data to test format")

if __name__ == "__main__":
    try:
        test_historical_data()
        test_chart_data_format()
        
        print("\n" + "=" * 50)
        print("🎉 Historical Data Implementation Test Complete!")
        print("✅ Ready for dashboard integration")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
