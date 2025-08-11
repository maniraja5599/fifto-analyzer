#!/usr/bin/env python3
"""
Direct test of market data to see current values
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer.market_data_v2 import get_market_data

def test_current_data():
    print("🔍 Testing Current Market Data Values...")
    print("=" * 50)
    
    data = get_market_data()
    
    print("📊 CURRENT VALUES FROM OUR API:")
    for symbol, info in data.items():
        print(f"  {symbol}: ₹{info['price']} (Source: {info.get('source', 'Unknown')})")
        
    print("\n📊 EXPECTED VALUES (from TradingView):")
    print(f"  NIFTY: ₹24,465.65")
    print(f"  BANKNIFTY: ₹55,232.20")
    print(f"  SENSEX: ₹80,104.87")
    
    print("\n🔍 DETAILED DATA:")
    for symbol, info in data.items():
        print(f"\n{symbol}:")
        for key, value in info.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    test_current_data()
