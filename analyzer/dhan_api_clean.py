"""
DhanHQ API Integration Module
============================

This module provides comprehensive integration with DhanHQ API for:
- Real-time market data (NIFTY, BANKNIFTY)
- Historical data for zone calculations
- Option chain data
- Live option prices
- Market quotes and fundamentals

IMPORTANT: This is for DATA API access only, NOT for trading operations.
DhanHQ API is used purely for market data retrieval and analysis.

Configuration:
- Add your DhanHQ API credentials to settings.py
- Ensure proper error handling and fallback mechanisms
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import time
import json

# Import DhanHQ correctly
try:
    from dhanhq import dhanhq
    DHANHQ_AVAILABLE = True
    print("✅ DhanHQ module imported successfully")
except ImportError as e:
    print(f"⚠️  DhanHQ module not available: {e}")
    DHANHQ_AVAILABLE = False
    dhanhq = None

class DhanHQIntegration:
    """
    Comprehensive DhanHQ API integration for market data
    """
    
    def __init__(self, client_id=None, access_token=None):
        """Initialize DhanHQ client with credentials"""
        self.client_id = client_id or os.environ.get('DHAN_CLIENT_ID')
        self.access_token = access_token or os.environ.get('DHAN_ACCESS_TOKEN')
        
        if not DHANHQ_AVAILABLE or dhanhq is None:
            print("⚠️  DhanHQ module not available. Using fallback mode.")
            self.client = None
        elif not self.client_id or not self.access_token:
            print("⚠️  DhanHQ credentials not found. Using fallback mode.")
            self.client = None
        else:
            try:
                # Initialize DhanHQ client correctly
                self.client = dhanhq(self.client_id, self.access_token)
                print("✅ DhanHQ client initialized successfully")
                print(f"🔑 Client ID: {self.client_id}")
            except Exception as e:
                print(f"❌ DhanHQ initialization failed: {e}")
                self.client = None
        
        # Symbol mappings for DhanHQ
        self.symbol_map = {
            'NIFTY': {'security_id': '13', 'exchange': 'NSE_EQ'},
            'BANKNIFTY': {'security_id': '25', 'exchange': 'NSE_EQ'},
            'NIFTY50': {'security_id': '13', 'exchange': 'NSE_EQ'},
            'BANKEX': {'security_id': '25', 'exchange': 'NSE_EQ'}
        }
    
    def get_current_price(self, instrument):
        """
        Get current market price for instrument using DhanHQ
        """
        if not self.client or not self.client_id or not self.access_token:
            return self._get_fallback_price(instrument)
        
        try:
            symbol_data = self.symbol_map.get(instrument.upper())
            if not symbol_data:
                print(f"❌ Symbol {instrument} not found in mapping")
                return self._get_fallback_price(instrument)
            
            print(f"🔄 Fetching DhanHQ price for {instrument}...")
            
            # Get live quote using DhanHQ ticker_data
            # DhanHQ API expects securities as a list
            securities = [{
                'securityId': symbol_data['security_id'],
                'exchangeSegment': symbol_data['exchange']
            }]
            
            quote_data = self.client.ticker_data(securities)
            
            print(f"📊 DhanHQ response for {instrument}: {quote_data}")
            
            if quote_data and isinstance(quote_data, list) and len(quote_data) > 0:
                data = quote_data[0]  # Get first result
                # Try different possible keys for price
                price_keys = ['LTP', 'lastPrice', 'close', 'last_price']
                price = None
                
                for key in price_keys:
                    if key in data and data[key]:
                        price = float(data[key])
                        break
                
                if price and price > 0:
                    print(f"✅ DhanHQ price for {instrument}: ₹{price:,.2f}")
                    return price
            
            print(f"⚠️  No valid price data from DhanHQ for {instrument}")
            return self._get_fallback_price(instrument)
                
        except Exception as e:
            print(f"❌ DhanHQ price fetch error for {instrument}: {e}")
            return self._get_fallback_price(instrument)
    
    def get_historical_data(self, instrument, period='1y'):
        """
        Get historical data for zone calculations
        """
        if not self.client or not self.client_id or not self.access_token:
            return None
        
        try:
            symbol_data = self.symbol_map.get(instrument.upper())
            if not symbol_data:
                return None
            
            # Calculate date range
            end_date = datetime.now()
            if period == '1y':
                start_date = end_date - timedelta(days=365)
            elif period == '6m':
                start_date = end_date - timedelta(days=180)
            elif period == '3m':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            print(f"🔄 Fetching DhanHQ historical data for {instrument}...")
            
            # Get historical data using DhanHQ
            # Correct parameters for historical_daily_data
            historical_data = self.client.historical_daily_data(
                security_id=symbol_data['security_id'],
                exchange_segment=symbol_data['exchange'],
                instrument_type="INDEX",
                from_date=start_date.strftime('%Y-%m-%d'),
                to_date=end_date.strftime('%Y-%m-%d')
            )
            
            print(f"📊 DhanHQ historical response for {instrument}: {type(historical_data)}, Length: {len(historical_data) if isinstance(historical_data, list) else 'N/A'}")
            
            if historical_data and isinstance(historical_data, list) and len(historical_data) > 0:
                # Convert to pandas DataFrame
                df_data = []
                for record in historical_data:
                    try:
                        df_data.append({
                            'Date': pd.to_datetime(record.get('date', record.get('timestamp', ''))),
                            'Open': float(record.get('open', 0)),
                            'High': float(record.get('high', 0)),
                            'Low': float(record.get('low', 0)),
                            'Close': float(record.get('close', 0)),
                            'Volume': int(record.get('volume', 0))
                        })
                    except (ValueError, TypeError) as e:
                        print(f"⚠️  Skipping invalid record: {e}")
                        continue
                
                if df_data:
                    df = pd.DataFrame(df_data)
                    df.set_index('Date', inplace=True)
                    df = df.sort_index()
                    
                    print(f"✅ DhanHQ historical data for {instrument}: {len(df)} records")
                    return df
            
            print(f"⚠️  No historical data from DhanHQ for {instrument}")
            return None
                
        except Exception as e:
            print(f"❌ DhanHQ historical data error for {instrument}: {e}")
            return None
    
    def get_option_chain(self, instrument):
        """
        Get option chain data from DhanHQ
        """
        if not self.client or not self.client_id or not self.access_token:
            return None
        
        try:
            symbol_data = self.symbol_map.get(instrument.upper())
            if not symbol_data:
                return None
            
            print(f"🔄 Fetching DhanHQ option chain for {instrument}...")
            
            # Get option chain using DhanHQ
            # Correct parameters for option_chain
            option_data = self.client.option_chain(
                under_security_id=symbol_data['security_id'],
                under_exchange_segment=symbol_data['exchange'],
                expiry="latest"  # Get latest expiry
            )
            
            print(f"📊 DhanHQ option chain response for {instrument}: {type(option_data)}")
            
            if option_data:
                return option_data
            
            print(f"⚠️  No option chain data from DhanHQ for {instrument}")
            return None
                
        except Exception as e:
            print(f"❌ DhanHQ option chain error for {instrument}: {e}")
            return None
    
    def _get_fallback_price(self, instrument):
        """Fallback prices when DhanHQ is not available"""
        fallback_prices = {
            'NIFTY': 24400.0,
            'BANKNIFTY': 55100.0,
            'NIFTY50': 24400.0,
            'BANKEX': 55100.0
        }
        return fallback_prices.get(instrument.upper(), 25000.0)
    
    def test_connection(self):
        """Test DhanHQ API connection"""
        if not self.client:
            return False, "Client not initialized"
        
        try:
            # Test with NIFTY ticker data
            securities = [{'securityId': '13', 'exchangeSegment': 'NSE_EQ'}]
            quote = self.client.ticker_data(securities)
            
            if quote and isinstance(quote, list) and len(quote) > 0:
                data = quote[0]
                price = data.get('LTP', data.get('last_price', 'N/A'))
                return True, f"Connection successful. NIFTY: ₹{price}"
            else:
                return False, "No data received"
                
        except Exception as e:
            return False, f"Connection failed: {e}"


# Global DhanHQ instance
dhan_api = DhanHQIntegration()


def get_dhan_price(instrument):
    """Helper function to get price from DhanHQ"""
    return dhan_api.get_current_price(instrument)


def get_dhan_historical(instrument, period='1y'):
    """Helper function to get historical data from DhanHQ"""
    return dhan_api.get_historical_data(instrument, period)


def get_dhan_option_chain(instrument):
    """Helper function to get option chain from DhanHQ"""
    return dhan_api.get_option_chain(instrument)


def test_dhan_connection():
    """Test DhanHQ connection"""
    return dhan_api.test_connection()
