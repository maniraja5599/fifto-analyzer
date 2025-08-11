#!/usr/bin/env python3
"""
Test the Django API endpoints for market data
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

# Now import Django modules
from django.test import Client
from django.urls import reverse

def test_api_endpoints():
    """Test the market data API endpoints"""
    print("🧪 Testing Django API Endpoints for Market Data...")
    print("=" * 60)
    
    try:
        # Create a test client
        client = Client()
        
        # Test market data API
        print("📊 Testing market data API endpoint...")
        response = client.get('/api/market-data/')
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Market data API working!")
                print(f"📈 Response: {json.dumps(data, indent=2)}")
            except:
                print(f"Response content: {response.content.decode()}")
        else:
            print(f"❌ API Error: {response.content.decode()}")
        
        # Test market status API
        print(f"\n📊 Testing market status API endpoint...")
        response = client.get('/api/market-status/')
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Market status API working!")
                print(f"📈 Response: {json.dumps(data, indent=2)}")
            except:
                print(f"Response content: {response.content.decode()}")
        else:
            print(f"❌ API Error: {response.content.decode()}")
        
        print(f"\n✅ API testing completed!")
        
    except Exception as e:
        print(f"❌ Error testing APIs: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_endpoints()
