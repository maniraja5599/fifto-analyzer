#!/usr/bin/env python3
"""
Market Data Service - Fetches data from yfinance once per minute
"""
import yfinance as yf
import json
import time
import threading
from datetime import datetime, timedelta
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        self.data_file = 'market_data_cache.json'
        self.running = False
        self.thread = None
        
        # Market symbols for yfinance
        self.symbols = {
            'NIFTY': '^NSEI',      # Nifty 50
            'BANKNIFTY': '^NSEBANK', # Bank Nifty  
            'SENSEX': '^BSESN',    # Sensex
            'VIX': '^INDIAVIX'     # India VIX
        }
        
        # Initialize with empty data
        self.market_data = {
            'NIFTY': {'current_price': 0, 'change': 0, 'change_percent': 0, 'last_updated': None},
            'BANKNIFTY': {'current_price': 0, 'change': 0, 'change_percent': 0, 'last_updated': None},
            'SENSEX': {'current_price': 0, 'change': 0, 'change_percent': 0, 'last_updated': None},
            'VIX': {'current_price': 0, 'change': 0, 'change_percent': 0, 'last_updated': None},
            'last_fetch': None,
            'status': 'initializing'
        }
        
        # Load existing data if available
        self.load_cached_data()
    
    def fetch_market_data(self):
        """Fetch market data from yfinance with multiple symbol options"""
        try:
            # Try multiple symbol formats for each index
            symbols = {
                'NIFTY': ['^NSEI', 'NSEI.NS', '^CNX_NIFTY'],
                'BANKNIFTY': ['^NSEBANK', 'NSEBANK.NS', '^NIFTY_BANK'], 
                'SENSEX': ['^BSESN', 'SENSEX.BO', '^BSE_SENSEX'],
                'VIX': ['^INDIAVIX', 'VIX.NS', '^INDIA_VIX']
            }
            
            market_data = {}
            
            for name, symbol_list in symbols.items():
                success = False
                for symbol in symbol_list:
                    try:
                        print(f"🔍 Trying {name} with symbol {symbol}...")
                        ticker = yf.Ticker(symbol)
                        
                        # Try to get current price from info first
                        info = ticker.info
                        current_price = None
                        
                        # Try different price fields
                        if 'regularMarketPrice' in info and info['regularMarketPrice']:
                            current_price = info['regularMarketPrice']
                        elif 'currentPrice' in info and info['currentPrice']:
                            current_price = info['currentPrice']
                        elif 'previousClose' in info and info['previousClose']:
                            current_price = info['previousClose']
                        
                        # If info doesn't work, try historical data
                        if not current_price:
                            hist = ticker.history(period="5d")
                            if not hist.empty:
                                current_price = hist['Close'].iloc[-1]
                        
                        if current_price and current_price > 0:
                            # Get previous close for change calculation
                            previous_close = current_price
                            if 'previousClose' in info and info['previousClose']:
                                previous_close = info['previousClose']
                            elif not hist.empty and len(hist) > 1:
                                previous_close = hist['Close'].iloc[-2]
                            
                            change = current_price - previous_close
                            change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
                            
                            market_data[name] = {
                                'current_price': round(float(current_price), 2),
                                'change': round(float(change), 2),
                                'change_percent': round(float(change_percent), 2),
                                'previous_close': round(float(previous_close), 2),
                                'last_updated': datetime.now().isoformat(),
                                'symbol': symbol
                            }
                            print(f"✅ {name}: {current_price} (using {symbol})")
                            success = True
                            break
                        
                    except Exception as e:
                        print(f"⚠️ Failed {symbol}: {e}")
                        continue
                    
                    # Rate limiting between attempts
                    time.sleep(1)
                
                # If no symbol worked, use fallback data
                if not success:
                    print(f"❌ All symbols failed for {name}, using fallback")
                    # Try to use cached data or create dummy data
                    cached = self.get_cached_data()
                    if cached and name in cached:
                        market_data[name] = cached[name]
                    else:
                        market_data[name] = {
                            'current_price': self.get_dummy_price(name),
                            'change': 0,
                            'change_percent': 0,
                            'previous_close': self.get_dummy_price(name),
                            'last_updated': datetime.now().isoformat(),
                            'symbol': symbol_list[0]
                        }
            
            # Save to cache
            cache_data = {
                **market_data,
                'timestamp': datetime.now().isoformat(),
                'source': 'yfinance'
            }
            
            with open('market_data_cache.json', 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"� Cache updated at {datetime.now().strftime('%H:%M:%S')}")
            return market_data
            
        except Exception as e:
            print(f"❌ Error in fetch_market_data: {e}")
            return self.get_cached_data()
    
    def get_dummy_price(self, name):
        """Get realistic dummy prices for testing"""
        dummy_prices = {
            'NIFTY': 24500.0,
            'BANKNIFTY': 51000.0,
            'SENSEX': 80000.0,
            'VIX': 15.0
        }
        return dummy_prices.get(name, 1000.0)
    
    def get_historical_data(self, symbol='NIFTY', period='1mo'):
        """Fetch historical data for charts"""
        try:
            yf_symbol = self.symbols.get(symbol, '^NSEI')
            ticker = yf.Ticker(yf_symbol)
            
            # Get historical data
            hist = ticker.history(period=period)
            
            # Convert to list of dictionaries
            historical_data = []
            for idx, row in hist.iterrows():
                date_str = str(idx)[:10]  # Get first 10 chars (YYYY-MM-DD)
                historical_data.append({
                    'Date': date_str,
                    'Open': round(float(row['Open']), 2),
                    'High': round(float(row['High']), 2),
                    'Low': round(float(row['Low']), 2),
                    'Close': round(float(row['Close']), 2),
                    'Volume': int(row['Volume']) if row['Volume'] > 0 else 0
                })
            
            return historical_data
            
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol}: {str(e)}")
            return []
    
    def save_cached_data(self):
        """Save market data to cache file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.market_data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving cache: {str(e)}")
    
    def load_cached_data(self):
        """Load market data from cache file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    cached_data = json.load(f)
                    
                # Check if cache is recent (less than 5 minutes old)
                if cached_data.get('last_fetch'):
                    last_fetch = datetime.fromisoformat(cached_data['last_fetch'])
                    if datetime.now() - last_fetch < timedelta(minutes=5):
                        self.market_data.update(cached_data)
                        logger.info("📁 Loaded recent cached market data")
                        return
                
                logger.info("📁 Cache found but outdated, will refresh")
        except Exception as e:
            logger.error(f"❌ Error loading cache: {str(e)}")
    
    def get_cached_data(self):
        """Get cached market data"""
        try:
            with open('market_data_cache.json', 'r') as f:
                cache = json.load(f)
                # Remove timestamp and source to get just the market data
                data = dict(cache)
                data.pop('timestamp', None)
                data.pop('source', None)
                return data
        except:
            return {}
    
    def get_dummy_price(self, name):
        """Get realistic dummy prices for testing"""
        dummy_prices = {
            'NIFTY': 24500.0,
            'BANKNIFTY': 51000.0,
            'SENSEX': 80000.0,
            'VIX': 15.0
        }
        return dummy_prices.get(name, 1000.0)
    
    def start_service(self):
        """Start the background market data service"""
        if self.running:
            logger.warning("⚠️ Service already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._service_loop, daemon=True)
        self.thread.start()
        logger.info("🚀 Market Data Service started")
    
    def stop_service(self):
        """Stop the background service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 Market Data Service stopped")
    
    def _service_loop(self):
        """Main service loop - fetch data every minute"""
        # Initial fetch
        self.fetch_market_data()
        
        while self.running:
            try:
                # Wait 60 seconds
                for _ in range(60):
                    if not self.running:
                        break
                    time.sleep(1)
                
                if self.running:
                    self.fetch_market_data()
                    
            except Exception as e:
                logger.error(f"❌ Error in service loop: {str(e)}")
                time.sleep(10)  # Wait 10 seconds before retrying
    
    def get_current_data(self):
        """Get current market data"""
        return self.market_data
    
    def is_market_hours(self):
        """Check if it's market hours (9:15 AM to 3:30 PM IST)"""
        now = datetime.now()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Check if it's a weekday and within market hours
        is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4
        is_market_time = market_open <= now <= market_close
        
        return is_weekday and is_market_time

# Global service instance
market_service = MarketDataService()

def start_market_service():
    """Start the market data service"""
    market_service.start_service()

def stop_market_service():
    """Stop the market data service"""
    market_service.stop_service()

def get_market_data():
    """Get current market data"""
    return market_service.get_current_data()

def get_historical_data(symbol='NIFTY', period='1mo'):
    """Get historical data for charts"""
    return market_service.get_historical_data(symbol, period)

if __name__ == "__main__":
    # Run as standalone service
    print("🚀 Starting Market Data Service...")
    try:
        market_service.start_service()
        
        # Keep running
        while True:
            time.sleep(10)
            data = market_service.get_current_data()
            print(f"📊 Status: {data.get('status', 'unknown')} | Last fetch: {data.get('last_fetch', 'never')}")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping service...")
        market_service.stop_service()
        print("✅ Service stopped")
