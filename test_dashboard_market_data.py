#!/usr/bin/env python3
"""
Test script to check if the dashboard market data loading is working with DhanHQ API
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

# Now import Django modules
from analyzer.market_data import get_market_data, get_market_status

def test_market_data():
    """Test the market data function"""
    print("🧪 Testing Market Data with DhanHQ Integration...")
    print("=" * 60)
    
    try:
        # Test market data
        print("📊 Fetching market data...")
        market_data = get_market_data()
        
        print(f"\n✅ Market data retrieved successfully!")
        print(f"📈 Number of symbols: {len(market_data)}")
        
        for symbol, data in market_data.items():
            print(f"\n🔸 {symbol}:")
            print(f"   Price: ₹{data['price']:,.2f}")
            print(f"   Change: {data['change']:+,.2f} ({data['change_percent']:+.2f}%)")
            print(f"   Status: {data['status']}")
            print(f"   Source: {data.get('source', 'Unknown')}")
            print(f"   Updated: {data['last_updated']}")
            if data.get('is_fallback'):
                print(f"   ⚠️  Using fallback data")
        
        # Test market status
        print(f"\n📈 Market Status:")
        status = get_market_status()
        print(f"   Open: {status['is_open']}")
        print(f"   Status: {status['status']}")
        
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing market data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_market_data()
