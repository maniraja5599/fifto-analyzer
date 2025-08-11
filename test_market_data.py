#!/usr/bin/env python3
"""
Quick test script to verify market data calculations
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, '/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

# Now import the market data module
from analyzer.market_data_v2 import get_market_data

def test_market_data():
    """Test market data retrieval and price calculations"""
    print("🔄 Testing Market Data Calculations...")
    print("=" * 50)
    
    try:
        # Get market data
        market_data = get_market_data()
        
        print(f"📊 Market Data Retrieved: {len(market_data)} instruments")
        print()
        
        # Display each instrument's data
        for symbol, data in market_data.items():
            if isinstance(data, dict):
                ltp = data.get('price', 0)  # Using 'price' field as LTP
                change = data.get('change', 0)
                change_percent = data.get('change_percent', 0)
                
                print(f"🏷️  Symbol: {symbol}")
                print(f"💰 LTP: ₹{ltp:.2f}")
                print(f"📈 Change: ₹{change:.2f}")
                print(f"📊 Change %: {change_percent:.2f}%")
                print("-" * 30)
            
        print("\n✅ Market data test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing market data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_market_data()
