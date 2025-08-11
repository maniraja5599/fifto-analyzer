#!/usr/bin/env python3
"""
Test the Django API endpoint that the dashboard JavaScript is calling
"""
import os
import sys
import django
import json

# Add the project directory to the Python path
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from django.test import Client

def test_api_response():
    print("🧪 Testing Django API Endpoint: /api/market-data/")
    print("=" * 60)
    
    client = Client()
    response = client.get('/api/market-data/')
    
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ API Response Structure:")
            print(json.dumps(data, indent=2))
            
            print(f"\n📈 Market Data Values:")
            if 'market_data' in data:
                for symbol, values in data['market_data'].items():
                    if values:
                        print(f"  {symbol.upper()}: ₹{values.get('price', 'N/A')} (Source: {values.get('source', 'Unknown')})")
            
        except Exception as e:
            print(f"❌ Error parsing JSON: {e}")
            print(f"Raw response: {response.content.decode()}")
    else:
        print(f"❌ API Error: {response.content.decode()}")

if __name__ == "__main__":
    test_api_response()
