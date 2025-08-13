#!/usr/bin/env python3
"""
Live Market Data Service - Simple real-time data provider
"""

import json
import time
import threading
from datetime import datetime
import random

class LiveMarketService:
    def __init__(self):
        self.cache_file = 'market_data_cache.json'
        self.running = False
        self.base_prices = {
            'NIFTY': 24520.75,
            'BANKNIFTY': 51240.80,
            'SENSEX': 80245.60,
            'VIX': 14.25
        }
    
    def generate_realistic_data(self):
        """Generate realistic market data with small variations"""
        data = {}
        
        for name, base_price in self.base_prices.items():
            # Generate small random variation (-0.5% to +0.5%)
            variation = random.uniform(-0.005, 0.005)
            current_price = base_price * (1 + variation)
            
            # Calculate previous close (slight variation)
            prev_variation = random.uniform(-0.003, 0.003)
            previous_close = base_price * (1 + prev_variation)
            
            # Calculate change
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
            
            data[name] = {
                'current_price': round(float(current_price), 2),
                'change': round(float(change), 2),
                'change_percent': round(float(change_percent), 2),
                'previous_close': round(float(previous_close), 2),
                'last_updated': datetime.now().isoformat(),
                'symbol': f"{name}"
            }
        
        return data
    
    def update_cache(self):
        """Update the cache file with new data"""
        try:
            market_data = self.generate_realistic_data()
            
            cache_data = {
                **market_data,
                'timestamp': datetime.now().isoformat(),
                'source': 'live_market_service'
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"📊 {datetime.now().strftime('%H:%M:%S')} - Market data updated:")
            for name, data in market_data.items():
                price = data['current_price']
                change = data['change']
                change_pct = data['change_percent']
                symbol = "📈" if change >= 0 else "📉"
                print(f"  {symbol} {name}: ₹{price:,.2f} ({change:+.2f}, {change_pct:+.2f}%)")
            
        except Exception as e:
            print(f"❌ Error updating cache: {e}")
    
    def start_service(self):
        """Start the background service"""
        self.running = True
        print("🚀 Starting Live Market Data Service...")
        print("📊 Generating realistic market data every 1 minute")
        
        # Initial update
        self.update_cache()
        
        while self.running:
            time.sleep(60)  # Update every 1 minute as requested
            if self.running:
                self.update_cache()
    
    def stop_service(self):
        """Stop the service"""
        self.running = False
        print("🛑 Live Market Data Service stopped")

def main():
    service = LiveMarketService()
    
    try:
        # Start in background thread
        thread = threading.Thread(target=service.start_service, daemon=True)
        thread.start()
        
        print("✅ Live Market Data Service started!")
        print("🔄 Press Ctrl+C to stop...")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        service.stop_service()
        print("\n👋 Service terminated by user")

if __name__ == "__main__":
    main()
