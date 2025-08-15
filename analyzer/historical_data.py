"""
Historical Market Data Module
Fetches historical data for NIFTY, BANKNIFTY, SENSEX using yfinance and DhanHQ
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import requests
from .dhan_api import DhanHQIntegration  # unified import
import time

class HistoricalDataFetcher:
    """Fetch historical market data from multiple sources"""
    
    def __init__(self):
        """Initialize the data fetcher"""
        # Direct unified DhanHQ integration instance (if credentials present)
        try:
            self.dhan_api = DhanHQIntegration()
        except Exception:
            self.dhan_api = None
            print("⚠️ DhanHQ credentials missing for historical data")
        
        self.symbols = {
            'NIFTY': '^NSEI',
            'BANKNIFTY': '^NSEBANK', 
            'SENSEX': '^BSESN'
        }
        
    def get_historical_data(self, symbol, period='1d', interval='5m'):
        """
        Get historical data for the given symbol
        
        Args:
            symbol: NIFTY, BANKNIFTY, SENSEX
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        
        Returns:
            Dict with OHLC data and timestamps
        """
        try:
            # Try DhanHQ first for recent data
            if period == '1d' and symbol in ['NIFTY', 'BANKNIFTY']:
                dhan_data = self._get_dhan_historical(symbol, interval)
                if dhan_data:
                    return dhan_data
            
            # Fallback to yfinance
            return self._get_yfinance_historical(symbol, period, interval)
            
        except Exception as e:
            print(f"❌ Error fetching historical data for {symbol}: {e}")
            return self._get_fallback_data(symbol)
            
    def _get_dhan_historical(self, symbol, interval='5m'):
        """Get historical data from DhanHQ (uses unified dhan_api implementation)"""
        try:
            api = DhanHQIntegration()
            # Map period internally: use 30d for intraday style
            df = api.get_historical_data(symbol, period='1m')  # shorter range for intraday if needed
            if df is None or df.empty:
                return None
            # Convert DataFrame to expected dict (timestamps and prices)
            df_tail = df.tail(60)  # limit points
            return {
                'symbol': symbol,
                'timestamps': [ts.strftime('%H:%M') for ts in df_tail.index],
                'prices': df_tail['Close'].round(2).tolist(),
                'open': df_tail['Open'].round(2).tolist(),
                'high': df_tail['High'].round(2).tolist(),
                'low': df_tail['Low'].round(2).tolist(),
                'volume': df_tail.get('Volume', pd.Series([0]*len(df_tail))).tolist(),
                'current': float(df_tail['Close'].iloc[-1]),
                'previous_close': float(df_tail['Close'].iloc[0]),
                'change': float(df_tail['Close'].iloc[-1] - df_tail['Close'].iloc[0]),
                'change_percent': float((df_tail['Close'].iloc[-1] - df_tail['Close'].iloc[0]) / df_tail['Close'].iloc[0] * 100) if df_tail['Close'].iloc[0] else 0,
                'period': 'custom',
                'interval': interval,
                'last_updated': datetime.now().strftime('%H:%M:%S')
            }
        except Exception as e:
            print(f"❌ Dhan historical error: {e}")
            return None
            
    def _get_yfinance_historical(self, symbol, period='1d', interval='5m'):
        """Get historical data from yfinance"""
        try:
            yf_symbol = self.symbols.get(symbol, symbol)
            
            # Create ticker object
            ticker = yf.Ticker(yf_symbol)
            
            # Get historical data
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                print(f"⚠️ No historical data found for {symbol}")
                return self._get_fallback_data(symbol)
            
            # Convert to our format
            data = {
                'symbol': symbol,
                'timestamps': [ts.strftime('%H:%M') if period == '1d' else ts.strftime('%m-%d') 
                              for ts in hist.index],
                'prices': hist['Close'].round(2).tolist(),
                'open': hist['Open'].round(2).tolist(),
                'high': hist['High'].round(2).tolist(), 
                'low': hist['Low'].round(2).tolist(),
                'volume': hist['Volume'].tolist() if 'Volume' in hist else [],
                'current': hist['Close'].iloc[-1] if not hist.empty else 0,
                'previous_close': hist['Close'].iloc[0] if len(hist) > 1 else hist['Close'].iloc[-1],
                'period': period,
                'interval': interval,
                'last_updated': datetime.now().strftime('%H:%M:%S')
            }
            
            # Calculate change
            if len(data['prices']) > 1:
                data['change'] = data['current'] - data['previous_close']
                data['change_percent'] = (data['change'] / data['previous_close']) * 100
            else:
                data['change'] = 0
                data['change_percent'] = 0
                
            print(f"✅ Fetched {len(data['prices'])} data points for {symbol}")
            return data
            
        except Exception as e:
            print(f"❌ yfinance error for {symbol}: {e}")
            return self._get_fallback_data(symbol)
            
    def _get_fallback_data(self, symbol):
        """Generate fallback historical data"""
        try:
            from datetime import datetime, timedelta
            import random
            
            # Base prices
            base_prices = {
                'NIFTY': 24500,
                'BANKNIFTY': 55000,
                'SENSEX': 80000
            }
            
            base_price = base_prices.get(symbol, 24500)
            
            # Generate 30 data points (6 hours * 5 min intervals)
            timestamps = []
            prices = []
            current_time = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
            current_price = base_price
            
            for i in range(30):
                timestamps.append(current_time.strftime('%H:%M'))
                
                # Add some realistic price movement
                change_percent = random.uniform(-0.5, 0.5)  # ±0.5%
                price_change = current_price * (change_percent / 100)
                current_price += price_change
                
                prices.append(round(current_price, 2))
                current_time += timedelta(minutes=5)
            
            data = {
                'symbol': symbol,
                'timestamps': timestamps,
                'prices': prices,
                'open': [base_price] * len(prices),
                'high': [p * 1.002 for p in prices],  # Slightly higher
                'low': [p * 0.998 for p in prices],   # Slightly lower
                'volume': [random.randint(1000, 5000) for _ in prices],
                'current': prices[-1],
                'previous_close': base_price,
                'change': prices[-1] - base_price,
                'change_percent': ((prices[-1] - base_price) / base_price) * 100,
                'period': '1d',
                'interval': '5m',
                'last_updated': datetime.now().strftime('%H:%M:%S')
            }
            
            print(f"🔄 Using fallback data for {symbol}")
            return data
            
        except Exception as e:
            print(f"❌ Fallback data generation error: {e}")
            return None
            
    def get_multiple_historical(self, symbols=['NIFTY', 'BANKNIFTY', 'SENSEX'], period='1d', interval='5m'):
        """Get historical data for multiple symbols"""
        results = {}
        
        for symbol in symbols:
            try:
                data = self.get_historical_data(symbol, period, interval)
                if data:
                    results[symbol] = data
                    time.sleep(0.1)  # Small delay to avoid rate limiting
            except Exception as e:
                print(f"❌ Error fetching {symbol}: {e}")
                continue
                
        return results

# Global instance
historical_fetcher = HistoricalDataFetcher()
