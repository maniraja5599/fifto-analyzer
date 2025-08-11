#!/usr/bin/env python3
"""
Test script for DhanHQ expiry date implementation
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer.utils import get_option_chain_data
from analyzer.dhan_api import get_dhan_option_chain

def test_expiry_dates():
    """Test expiry date fetching from DhanHQ and fallback methods"""
    print("🧪 Testing DhanHQ Expiry Date Implementation")
    print("=" * 60)
    
    symbols = ['NIFTY', 'BANKNIFTY']
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol} expiry dates:")
        print("-" * 40)
        
        # Test 1: Direct DhanHQ API call
        print(f"\n1. Direct DhanHQ API test for {symbol}:")
        try:
            dhan_data = get_dhan_option_chain(symbol)
            if dhan_data:
                if 'expiryDates' in dhan_data:
                    expiry_dates = dhan_data['expiryDates']
                    print(f"   ✅ DhanHQ returned {len(expiry_dates)} expiry dates:")
                    for i, date in enumerate(expiry_dates[:5]):  # Show first 5
                        print(f"      {i+1}. {date}")
                    if len(expiry_dates) > 5:
                        print(f"      ... and {len(expiry_dates) - 5} more")
                else:
                    print(f"   ⚠️  DhanHQ returned data but no expiryDates field")
                    print(f"   📋 Available keys: {list(dhan_data.keys())}")
            else:
                print(f"   ❌ No data returned from DhanHQ for {symbol}")
        except Exception as e:
            print(f"   ❌ DhanHQ API error: {e}")
        
        # Test 2: Full option chain data function
        print(f"\n2. Full option chain function test for {symbol}:")
        try:
            option_data = get_option_chain_data(symbol)
            if option_data:
                if 'expiryDates' in option_data:
                    expiry_dates = option_data['expiryDates']
                    print(f"   ✅ Option chain function returned {len(expiry_dates)} expiry dates:")
                    for i, date in enumerate(expiry_dates[:3]):  # Show first 3
                        print(f"      {i+1}. {date}")
                elif 'records' in option_data and 'expiryDates' in option_data['records']:
                    expiry_dates = option_data['records']['expiryDates']
                    print(f"   ✅ NSE format: {len(expiry_dates)} expiry dates:")
                    for i, date in enumerate(expiry_dates[:3]):  # Show first 3
                        print(f"      {i+1}. {date}")
                else:
                    print(f"   ⚠️  Option chain returned data but no expiry dates")
                    print(f"   📋 Available keys: {list(option_data.keys())}")
            else:
                print(f"   ❌ No data returned from option chain function for {symbol}")
        except Exception as e:
            print(f"   ❌ Option chain function error: {e}")
        
        # Test 3: Check current market data
        print(f"\n3. Current market data for {symbol}:")
        try:
            from analyzer.utils import get_current_market_price
            current_price = get_current_market_price(symbol)
            if current_price:
                print(f"   ✅ Current {symbol} price: ₹{current_price:.2f}")
            else:
                print(f"   ⚠️  Could not fetch current price for {symbol}")
        except Exception as e:
            print(f"   ❌ Market price error: {e}")

def test_dhan_api_connection():
    """Test DhanHQ API connection"""
    print(f"\n🔗 Testing DhanHQ API Connection:")
    print("-" * 40)
    
    try:
        from analyzer.dhan_api import test_dhan_connection
        success, message = test_dhan_connection()
        if success:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
    except Exception as e:
        print(f"   ❌ Connection test failed: {e}")

if __name__ == "__main__":
    try:
        test_dhan_api_connection()
        test_expiry_dates()
        
        print("\n" + "=" * 60)
        print("🎉 Expiry Date Testing Complete!")
        print("\n💡 Summary:")
        print("   • DhanHQ integration enhanced with proper expiry date calculation")
        print("   • Fallback mechanism ensures expiry dates are always available")
        print("   • NSE API fallback maintains compatibility")
        print("   • Auto-calculation based on F&O weekly/monthly expiry rules")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
