"""
Market Data Module - NSE Data Only
Provides current market prices and historical data for Indian indices
"""
import yfinance as yf
import requests
import logging
import time
from django.conf import settings

logger = logging.getLogger(__name__)

# NSE symbol mappings
MARKET_SYMBOLS = {
    'NIFTY': '^NSEI',
    'BANKNIFTY': '^NSEBANK',
    'SENSEX': '^BSESN',
    'VIX': '^INDIAVIX'
}

def get_market_data():
    """
    Fetch current market data for major Indian indices using yfinance
    Returns a dictionary with current prices and changes
    """
    market_data = {}
    
    try:
        for name, yahoo_symbol in MARKET_SYMBOLS.items():
            try:
                # Add small delay between requests
                if name != 'NIFTY':
                    time.sleep(0.5)
                
                # Get current price using yfinance
                ticker = yf.Ticker(yahoo_symbol)
                info = ticker.info
                hist = ticker.history(period="2d")
                
                if not hist.empty and len(hist) >= 1:
                    current_price = hist['Close'].iloc[-1]
                    
                    # Calculate change if we have at least 2 days of data
                    if len(hist) >= 2:
                        previous_close = hist['Close'].iloc[-2]
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100
                    else:
                        change = 0
                        change_percent = 0
                    
                    market_data[name] = {
                        'current_price': round(current_price, 2),
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2),
                        'symbol': yahoo_symbol,
                        'source': 'yfinance'
                    }
                    
                    logger.info(f"✅ {name}: ₹{current_price:.2f} ({change:+.2f}, {change_percent:+.2f}%)")
                else:
                    logger.warning(f"⚠️ No price data available for {name}")
                    
            except Exception as e:
                logger.error(f"❌ Error fetching data for {name}: {str(e)}")
                # Add fallback data to prevent UI errors
                market_data[name] = {
                    'current_price': 0,
                    'change': 0,
                    'change_percent': 0,
                    'symbol': yahoo_symbol,
                    'source': 'fallback',
                    'error': str(e)
                }
                
    except Exception as e:
        logger.error(f"❌ Error in market data fetch: {str(e)}")
    
    return market_data

def get_market_status():
    """
    Get Indian market status (Open/Closed) based on time
    """
    from datetime import datetime, time as dt_time
    import pytz
    
    try:
        # Indian market hours: 9:15 AM to 3:30 PM IST, Monday to Friday
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return {
                'status': 'Closed',
                'reason': 'Weekend',
                'next_open': 'Monday 9:15 AM IST'
            }
        
        # Market hours
        market_open = dt_time(9, 15)  # 9:15 AM
        market_close = dt_time(15, 30)  # 3:30 PM
        current_time = now.time()
        
        if market_open <= current_time <= market_close:
            return {
                'status': 'Open',
                'current_time': now.strftime('%H:%M:%S IST'),
                'closes_at': '15:30 IST'
            }
        else:
            return {
                'status': 'Closed',
                'reason': 'After hours' if current_time > market_close else 'Before hours',
                'next_open': 'Today 9:15 AM IST' if current_time < market_open else 'Tomorrow 9:15 AM IST'
            }
            
    except Exception as e:
        logger.error(f"❌ Error getting market status: {str(e)}")
        return {
            'status': 'Unknown',
            'error': str(e)
        }

def get_historical_data(symbol_name, period='1mo'):
    """
    Get historical data for a symbol using yfinance
    """
    try:
        yahoo_symbol = MARKET_SYMBOLS.get(symbol_name.upper())
        if not yahoo_symbol:
            logger.error(f"Symbol {symbol_name} not found in mappings")
            return None
            
        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            logger.warning(f"No historical data for {symbol_name}")
            return None
            
        # Convert to list of dictionaries for easier consumption
        data = []
        for index, row in hist.iterrows():
            date_str = str(index)[:10]  # Get YYYY-MM-DD part
            data.append({
                'date': date_str,
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume']) if 'Volume' in row else 0
            })
            
        logger.info(f"✅ Historical data for {symbol_name}: {len(data)} records")
        return data
        
    except Exception as e:
        logger.error(f"❌ Error getting historical data for {symbol_name}: {str(e)}")
        return None

def get_current_price(symbol_name):
    """
    Get current price for a symbol using yfinance
    """
    try:
        yahoo_symbol = MARKET_SYMBOLS.get(symbol_name.upper())
        if not yahoo_symbol:
            logger.error(f"Symbol {symbol_name} not found in mappings")
            return None
            
        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(period="1d")
        
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            logger.info(f"✅ Current price for {symbol_name}: ₹{current_price:.2f}")
            return {
                'price': round(current_price, 2),
                'symbol': yahoo_symbol,
                'source': 'yfinance'
            }
        else:
            logger.warning(f"No current price data for {symbol_name}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error getting current price for {symbol_name}: {str(e)}")
        return None
