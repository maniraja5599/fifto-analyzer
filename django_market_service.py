#!/usr/bin/env python3
"""
Django integration for Market Data Service
"""
import os
import sys
import django
from threading import Thread
import atexit

# Add the project directory to Python path
project_root = '/Users/maniraja/Desktop/Nifty Selling Git/fifto-analyzer'
sys.path.insert(0, project_root)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

try:
    django.setup()
except Exception as e:
    print(f"⚠️ Django setup warning: {e}")

# Import the market service
from market_data_service import market_service

def start_market_service():
    """Start the market data service for Django"""
    print("🚀 Starting Market Data Service for Django...")
    market_service.start_service()
    
    # Register cleanup on exit
    atexit.register(stop_market_service)
    
    return market_service

def stop_market_service():
    """Stop the market data service"""
    print("🛑 Stopping Market Data Service...")
    market_service.stop_service()

def get_django_market_data():
    """Get market data for Django views"""
    return market_service.get_current_data()

def manual_refresh_django_market_data():
    """Manually refresh market data for Django views"""
    print("🔄 Django manual market data refresh...")
    return market_service.manual_refresh()

def get_django_historical_data(symbol='NIFTY', period='1mo'):
    """Get historical data for Django views"""
    return market_service.get_historical_data(symbol, period)

# Auto-start disabled - service will be started on-demand only
if __name__ != "__main__":
    # DISABLED: Automatic service startup removed for manual control
    print("📝 Market data service available on-demand (automatic startup disabled)")
    # try:
    #     if not market_service.running:
    #         start_market_service()
    # except Exception as e:
    #     print(f"⚠️ Market service startup warning: {e}")

if __name__ == "__main__":
    # Run standalone
    try:
        start_market_service()
        
        import time
        print("✅ Market Data Service running. Press Ctrl+C to stop.")
        while True:
            time.sleep(10)
            data = market_service.get_current_data()
            print(f"📊 Status: {data.get('status')} | Last: {data.get('last_fetch', 'never')}")
            
    except KeyboardInterrupt:
        stop_market_service()
        print("✅ Service stopped")
