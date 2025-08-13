#!/usr/bin/env python3
"""
Initialize market data service for the dashboard
"""
import os
import sys

# Add project to path
project_path = '/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer'
sys.path.insert(0, project_path)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

try:
    import django
    django.setup()
    
    # Import and start the market service
    from market_data_service import market_service
    
    print("🚀 Starting market data service...")
    
    # Fetch initial data
    market_service.fetch_market_data()
    
    # Start the background service
    market_service.start_service()
    
    print("✅ Market data service started successfully!")
    
    # Show current data
    data = market_service.get_current_data()
    print("\n📊 Current Market Data:")
    for symbol, info in data.items():
        if symbol not in ['last_fetch', 'status']:
            price = info.get('current_price', 0)
            change = info.get('change_percent', 0)
            print(f"  {symbol}: ₹{price:,.2f} ({change:+.2f}%)")
    
    print(f"\n🔄 Service will update every minute...")
    print(f"📈 Status: {data.get('status', 'unknown')}")
    
except Exception as e:
    print(f"❌ Error starting market service: {e}")
    import traceback
    traceback.print_exc()
