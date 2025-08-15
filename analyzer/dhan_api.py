"""
DhanHQ API Integration Module - UPDATED v2.0
============================================

Complete DhanHQ API v2 integration based on official documentation:
https://docs.dhanhq.co/docs/v2/market-quote/

Key Features:
- Real-time market data using POST /marketfeed/ltp
- OHLC data using POST /marketfeed/ohlc  
- Full market quotes using POST /marketfeed/quote
- Proper rate limiting (1 request/second for market data)
- Correct security IDs and exchange segments

IMPORTANT: This is for DATA API access only, NOT for trading operations.
"""

import os
import requests
import time
from datetime import datetime, timedelta  # added timedelta
import logging
import pandas as pd  # added pandas earlier so pd is defined

logger = logging.getLogger(__name__)

class DhanHQIntegration:
    """
    Complete DhanHQ API v2 integration for market data
    Based on official documentation: https://docs.dhanhq.co/docs/v2/
    """
    
    def __init__(self, client_id=None, access_token=None):
        """Initialize DhanHQ client with credentials"""
        # Try to load from Django settings first, then environment variables
        try:
            from django.conf import settings
            self.client_id = client_id or getattr(settings, 'DHAN_CLIENT_ID', None) or os.environ.get('DHAN_CLIENT_ID')
            self.access_token = access_token or getattr(settings, 'DHAN_ACCESS_TOKEN', None) or os.environ.get('DHAN_ACCESS_TOKEN')
        except:
            # Fallback to environment variables if Django settings not available
            self.client_id = client_id or os.environ.get('DHAN_CLIENT_ID')
            self.access_token = access_token or os.environ.get('DHAN_ACCESS_TOKEN')
        
        # API endpoints
        self.base_url = "https://api.dhan.co/v2"
        
        # Headers for REST API calls (updated as per documentation)
        self.headers = {
            'access-token': self.access_token,
            'client-id': self.client_id,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Updated symbol mappings based on DhanHQ documentation
        # These are common index security IDs with instrument types
        self.symbol_map = {
            'NIFTY': {'security_id': 13, 'exchange': 'IDX_I', 'instrument': 'INDEX', 'name': 'NIFTY 50'},
            'BANKNIFTY': {'security_id': 25, 'exchange': 'IDX_I', 'instrument': 'INDEX', 'name': 'BANK NIFTY'}, 
            'SENSEX': {'security_id': 51, 'exchange': 'IDX_I', 'instrument': 'INDEX', 'name': 'BSE SENSEX'}
        }
        
        # Rate limiting - More conservative to avoid API limits
        self.last_request_time = 0
        self.rate_limit_delay = 2.0  # 2 seconds between requests to be extra safe
        
        # Simple in-memory cache to reduce API calls
        self.cache = {}
        self.cache_duration = 30  # Cache data for 30 seconds to reduce API calls
        
        if not self.client_id or not self.access_token:
            print("⚠️  DhanHQ credentials not found. Using fallback mode.")
        else:
            print("✅ DhanHQ API v2 initialized successfully")
            print(f"🔑 Client ID: {self.client_id}")
    
    def _rate_limit(self):
        """Enforce rate limiting as per DhanHQ guidelines"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_cache_key(self, method, params):
        """Generate cache key for request"""
        return f"{method}_{hash(str(sorted(params.items())))}"
    
    def _get_cached_data(self, cache_key):
        """Get data from cache if still valid"""
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_duration:
                print(f"📋 Using cached data for {cache_key}")
                return cached_data
        return None
    
    def _set_cached_data(self, cache_key, data):
        """Store data in cache with timestamp"""
        self.cache[cache_key] = (time.time(), data)
        # Clean old cache entries to prevent memory buildup
        current_time = time.time()
        expired_keys = [k for k, (t, _) in self.cache.items() if current_time - t > self.cache_duration * 2]
        for k in expired_keys:
            del self.cache[k]
    
    def get_current_price(self, instrument):
        """
        Get current market price using DhanHQ Market Quote LTP API
        Endpoint: POST /marketfeed/ltp
        
        Based on documentation: https://docs.dhanhq.co/docs/v2/market-quote/#ticker-data
        """
        if not self.client_id or not self.access_token:
            return self._get_fallback_price(instrument)
        
        # Check cache first to reduce API calls
        cache_key = self._get_cache_key('ltp', {'instrument': instrument})
        cached_result = self._get_cached_data(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            symbol_data = self.symbol_map.get(instrument.upper())
            if not symbol_data:
                print(f"❌ Symbol {instrument} not found in mapping")
                return self._get_fallback_price(instrument)
            
            # Apply rate limiting
            self._rate_limit()
            
            print(f"🔄 Fetching DhanHQ LTP for {instrument}...")
            
            # Prepare request according to DhanHQ API v2 documentation
            # Format: {"IDX_I": [13]} for indices
            request_body = {
                symbol_data['exchange']: [symbol_data['security_id']]
            }
            
            url = f"{self.base_url}/marketfeed/ltp"
            
            print(f"📊 Request URL: {url}")
            print(f"📊 Request Body: {request_body}")
            print(f"📊 Headers: {dict(self.headers)}")
            
            response = requests.post(url, headers=self.headers, json=request_body, timeout=10)
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📊 Response Content: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success' and 'data' in data:
                    # Navigate through the response structure as per documentation
                    exchange_data = data['data'].get(symbol_data['exchange'], {})
                    security_data = exchange_data.get(str(symbol_data['security_id']), {})
                    
                    if 'last_price' in security_data:
                        price = float(security_data['last_price'])
                        result = price
                        print(f"✅ DhanHQ LTP for {instrument}: ₹{price:,.2f}")
                        
                        # Cache the successful result
                        self._set_cached_data(cache_key, result)
                        return result
                        
                print(f"⚠️  No valid price data from DhanHQ for {instrument}")
                return self._get_fallback_price(instrument)
                
            elif response.status_code == 429:
                print(f"⚠️  Rate limit exceeded for {instrument} - will retry later")
                return self._get_fallback_price(instrument)
                
            else:
                print(f"❌ DhanHQ API error {response.status_code} for {instrument}: {response.text}")
                return self._get_fallback_price(instrument)
                
        except Exception as e:
            print(f"❌ DhanHQ price fetch error for {instrument}: {e}")
            return self._get_fallback_price(instrument)
    
    def get_ohlc_data(self, instrument):
        """
        Get OHLC data using DhanHQ OHLC API
        Endpoint: POST /marketfeed/ohlc
        """
        if not self.client_id or not self.access_token:
            return None
        
        try:
            symbol_data = self.symbol_map.get(instrument.upper())
            if not symbol_data:
                return None
            
            # Apply rate limiting
            self._rate_limit()
            
            request_body = {
                symbol_data['exchange']: [symbol_data['security_id']]
            }
            
            url = f"{self.base_url}/marketfeed/ohlc"
            
            response = requests.post(url, headers=self.headers, json=request_body, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success' and 'data' in data:
                    exchange_data = data['data'].get(symbol_data['exchange'], {})
                    security_data = exchange_data.get(str(symbol_data['security_id']), {})
                    
                    if 'last_price' in security_data and 'ohlc' in security_data:
                        result = {
                            'last_price': float(security_data['last_price']),
                            'open': float(security_data['ohlc'].get('open', 0)),
                            'high': float(security_data['ohlc'].get('high', 0)),
                            'low': float(security_data['ohlc'].get('low', 0)),
                            'close': float(security_data['ohlc'].get('close', 0))
                        }
                        print(f"✅ DhanHQ OHLC for {instrument}: {result}")
                        return result
                        
        except Exception as e:
            print(f"❌ DhanHQ OHLC fetch error for {instrument}: {e}")
        
        return None
    
    def get_current_prices(self, instruments):
        """Batch fetch current prices (LTP) for a list of instruments with one API call per exchange."""
        if not self.client_id or not self.access_token:
            return {sym: self._get_fallback_price(sym) for sym in instruments}
        # Group security IDs by exchange
        exchange_map = {}
        symbol_lookup = {}
        for sym in instruments:
            data = self.symbol_map.get(sym.upper())
            if not data:
                continue
            exchange_map.setdefault(data['exchange'], set()).add(data['security_id'])
            symbol_lookup[(data['exchange'], str(data['security_id']))] = sym.upper()
        if not exchange_map:
            return {}
        request_body = {ex: list(ids) for ex, ids in exchange_map.items()}
        self._rate_limit()
        url = f"{self.base_url}/marketfeed/ltp"
        try:
            resp = requests.post(url, headers=self.headers, json=request_body, timeout=10)
            result = {}
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                for ex, sec_dict in data.items():
                    for sec_id, payload in sec_dict.items():
                        sym = symbol_lookup.get((ex, sec_id))
                        if sym and isinstance(payload, dict) and 'last_price' in payload:
                            try:
                                result[sym] = float(payload['last_price'])
                            except (TypeError, ValueError):
                                result[sym] = self._get_fallback_price(sym)
            # Fill fallbacks for any missing symbols
            for sym in instruments:
                us = sym.upper()
                if us not in result:
                    result[us] = self._get_fallback_price(us)
            return result
        except Exception as e:
            print(f"❌ Batch LTP error: {e}")
            return {sym.upper(): self._get_fallback_price(sym) for sym in instruments}

    def get_ohlc_data_batch(self, instruments):
        """Batch fetch OHLC for list of instruments using single OHLC call per exchange."""
        if not self.client_id or not self.access_token:
            return {}
        exchange_map = {}
        symbol_lookup = {}
        for sym in instruments:
            data = self.symbol_map.get(sym.upper())
            if not data:
                continue
            exchange_map.setdefault(data['exchange'], set()).add(data['security_id'])
            symbol_lookup[(data['exchange'], str(data['security_id']))] = sym.upper()
        if not exchange_map:
            return {}
        request_body = {ex: list(ids) for ex, ids in exchange_map.items()}
        self._rate_limit()
        url = f"{self.base_url}/marketfeed/ohlc"
        results = {}
        try:
            resp = requests.post(url, headers=self.headers, json=request_body, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                for ex, sec_dict in data.items():
                    for sec_id, payload in sec_dict.items():
                        sym = symbol_lookup.get((ex, sec_id))
                        if sym and isinstance(payload, dict) and 'ohlc' in payload:
                            o = payload.get('ohlc', {})
                            try:
                                results[sym] = {
                                    'last_price': float(payload.get('last_price', 0) or 0),
                                    'open': float(o.get('open', 0) or 0),
                                    'high': float(o.get('high', 0) or 0),
                                    'low': float(o.get('low', 0) or 0),
                                    'close': float(o.get('close', 0) or 0)
                                }
                            except (TypeError, ValueError):
                                results[sym] = None
            return results
        except Exception as e:
            print(f"❌ Batch OHLC error: {e}")
            return results

    def get_historical_data(self, instrument, period='1y'):
        """
        Get historical data for zone calculations
        Endpoint: POST /v2/charts/historical (DhanHQ API v2)
        
        Based on DhanHQ API v2 documentation:
        https://dhanhq.co/docs/v2/historical-data/
        """
        if not self.client_id or not self.access_token:
            return None
        
        # Check cache first
        cache_key = self._get_cache_key('historical', {'instrument': instrument, 'period': period})
        cached_result = self._get_cached_data(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            symbol_data = self.symbol_map.get(instrument.upper())
            if not symbol_data:
                print(f"❌ Symbol data not found for {instrument}")
                return None
            
            # Apply rate limiting
            self._rate_limit()
            
            # Date range calculation based on period
            end_date = datetime.now()
            if period == '1d':
                start_date = end_date - timedelta(days=1)
            elif period == '1w':
                start_date = end_date - timedelta(weeks=1)
            elif period == '1m':
                start_date = end_date - timedelta(days=30)
            elif period == '3m':
                start_date = end_date - timedelta(days=90)
            elif period == '6m':
                start_date = end_date - timedelta(days=180)
            elif period == '1y':
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=30)
            
            print(f"🔄 Fetching DhanHQ historical data for {instrument}...")
            
            # Prepare request according to DhanHQ API v2 documentation
            # Based on: https://dhanhq.co/docs/v2/historical-data/#daily-historical-data
            request_body = {
                "securityId": str(symbol_data['security_id']),  # Must be string according to docs
                "exchangeSegment": symbol_data['exchange'],
                "instrument": symbol_data.get('instrument', 'INDEX'),  # Required field
                "expiryCode": 0,  # Required for all instruments
                "oi": False,  # Boolean for open interest data
                "fromDate": start_date.strftime('%Y-%m-%d'),
                "toDate": end_date.strftime('%Y-%m-%d')
            }
            
            # Use correct v2 endpoint (not /v2/charts/historical but /charts/historical)
            url = f"{self.base_url}/charts/historical"
            
            print(f"📊 Historical Request URL: {url}")
            print(f"📊 Historical Request Body: {request_body}")
            
            response = requests.post(url, headers=self.headers, json=request_body, timeout=10)
            
            print(f"📊 Historical Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Historical Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
                
                # DhanHQ v2 returns data as direct arrays (not nested in 'data' field)
                # Check for the required arrays directly in response
                if all(key in data for key in ['open', 'high', 'low', 'close', 'timestamp']):
                    # Convert to pandas DataFrame
                    df_data = []
                    
                    for i in range(len(data['timestamp'])):
                        try:
                            df_data.append({
                                'Date': pd.to_datetime(data['timestamp'][i], unit='s'),
                                'Open': float(data['open'][i]),
                                'High': float(data['high'][i]),
                                'Low': float(data['low'][i]),
                                'Close': float(data['close'][i]),
                                'Volume': float(data.get('volume', [0] * len(data['timestamp']))[i])
                            })
                        except (ValueError, IndexError) as e:
                            print(f"⚠️ Skipping invalid data point {i}: {e}")
                            continue
                    
                    if df_data:
                        result = pd.DataFrame(df_data)
                        result.set_index('Date', inplace=True)
                        print(f"✅ DhanHQ historical data: {len(result)} records for {instrument}")
                        
                        # Cache the result
                        self._set_cached_data(cache_key, result)
                        return result
                    else:
                        print(f"❌ No valid data points found in response")
                else:
                    print(f"📊 Missing required fields in response. Available keys: {list(data.keys())}")
                    print(f"📊 Response sample: {str(data)[:500]}")
                
            else:
                print(f"❌ DhanHQ historical API error: {response.status_code}")
                if response.status_code == 400:
                    error_text = response.text
                    print(f"📊 Error response: {error_text}")
                    print("💡 Check: securityId format, exchangeSegment, instrument type, date format")
                elif response.status_code == 429:
                    print("⚠️ Rate limit exceeded - will use fallback data")
                
        except Exception as e:
            print(f"❌ Historical data error for {instrument}: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def get_option_chain(self, instrument):
        """
        Get option chain data from DhanHQ with all expiry dates
        Endpoint: POST /v2/optionchain
        
        Based on DhanHQ API v2 documentation:
        https://dhanhq.co/docs/v2/option-chain/
        """
        if not self.client_id or not self.access_token:
            print(f"⚠️  DhanHQ credentials not available for option chain")
            return None
        
        # Check cache first - option chain cache for 30 seconds
        cache_key = self._get_cache_key('optionchain', {'instrument': instrument})
        cached_result = self._get_cached_data(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            symbol_data = self.symbol_map.get(instrument.upper())
            if not symbol_data:
                print(f"⚠️  Symbol mapping not found for {instrument}")
                return None
            
            print(f"🔄 Fetching DhanHQ option chain for {instrument}...")
            
            # First, get available expiry dates using the expiry list endpoint
            expiry_dates = self._get_expiry_list_from_api(instrument)
            
            if not expiry_dates:
                # Fallback: calculate next few expiry dates
                expiry_dates = self._calculate_expiry_dates(instrument)
            
            # Use the nearest expiry date for the main option chain request
            nearest_expiry = expiry_dates[0] if expiry_dates else self._get_next_expiry()
            
            # Apply special rate limiting for option chain (1 request per 3 seconds)
            self._option_chain_rate_limit()
            
            # Prepare request according to DhanHQ API v2 documentation
            # Note: UnderlyingScrip should be integer, not string
            request_body = {
                "UnderlyingScrip": symbol_data['security_id'],  # Integer, not string
                "UnderlyingSeg": symbol_data['exchange'],
                "Expiry": nearest_expiry  # Format: YYYY-MM-DD
            }
            
            url = f"{self.base_url}/optionchain"
            
            print(f"📊 Option Chain Request - Symbol: {instrument}, Expiry: {nearest_expiry}")
            print(f"📊 Option Chain Request Body: {request_body}")
            
            response = requests.post(url, headers=self.headers, json=request_body, timeout=15)
            
            print(f"📊 Option Chain Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Option Chain Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
                
                # Process and enhance the response with all expiry dates
                if 'data' in data and data['data']:
                    # Add all available expiry dates to the response
                    data['expiryDates'] = expiry_dates
                    data['symbol'] = instrument
                    data['underlying'] = symbol_data['security_id']
                    
                    # Count strikes with valid option data
                    strike_count = 0
                    if 'oc' in data['data']:
                        strike_count = len(data['data']['oc'])
                    
                    print(f"✅ DhanHQ option chain for {instrument}: {strike_count} strikes, {len(expiry_dates)} expiry dates")
                    
                    # Cache the result
                    self._set_cached_data(cache_key, data)
                    return data
                else:
                    print(f"📊 Empty or invalid option chain response structure")
                    print(f"📊 Response preview: {str(data)[:300]}")
            
            elif response.status_code == 400:
                error_text = response.text
                print(f"📊 Option Chain 400 Error: {error_text}")
                print("💡 Check: UnderlyingScrip format (should be integer), UnderlyingSeg, Expiry date format")
            elif response.status_code == 429:
                print("⚠️ Option chain rate limit exceeded - using fallback")
            else:
                print(f"❌ Option chain API error: {response.status_code}")
                print(f"📊 Response: {response.text[:200]}")
            
            print(f"⚠️  No option chain data from DhanHQ for {instrument}")
            return None
                
        except Exception as e:
            print(f"❌ DhanHQ option chain error for {instrument}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _option_chain_rate_limit(self):
        """
        Special rate limiting for option chain API (1 request per 3 seconds)
        """
        if not hasattr(self, 'last_option_chain_request'):
            self.last_option_chain_request = 0
        
        current_time = time.time()
        time_since_last_request = current_time - self.last_option_chain_request
        
        if time_since_last_request < 3.0:  # 3 seconds minimum
            sleep_time = 3.0 - time_since_last_request
            print(f"⏱️ Option chain rate limit: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.last_option_chain_request = time.time()
    
    def _get_expiry_list_from_api(self, instrument):
        """
        Get available expiry dates from DhanHQ expiry list API
        Endpoint: POST /v2/optionchain/expirylist
        """
        try:
            symbol_data = self.symbol_map.get(instrument.upper())
            if not symbol_data:
                return []
            
            # Apply rate limiting
            self._rate_limit()
            
            # Prepare request for expiry list
            request_body = {
                "UnderlyingScrip": symbol_data['security_id'],  # Integer
                "UnderlyingSeg": symbol_data['exchange']
            }
            
            url = f"{self.base_url}/optionchain/expirylist"
            
            print(f"📅 Fetching expiry list for {instrument}...")
            
            response = requests.post(url, headers=self.headers, json=request_body, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'data' in data:
                    expiry_list = data['data']
                    print(f"📅 Got {len(expiry_list)} expiry dates from DhanHQ API")
                    return expiry_list[:10]  # Return first 10 expiries
            
            print(f"⚠️ Could not fetch expiry list from API (status: {response.status_code})")
            
        except Exception as e:
            print(f"⚠️ Error fetching expiry list: {e}")
        
        return []
    
    def _get_available_expiry_dates(self, instrument):
        """
        Try to get available expiry dates from DhanHQ expiry list API
        """
        try:
            # Use the new expiry list API endpoint
            return self._get_expiry_list_from_api(instrument)
        except Exception as e:
            print(f"⚠️  Could not fetch expiry dates from DhanHQ API: {e}")
            return self._calculate_expiry_dates(instrument)
    
    def _calculate_expiry_dates(self, instrument):
        """
        Calculate likely expiry dates for NIFTY/BANKNIFTY based on F&O rules
        """
        try:
            from datetime import datetime, timedelta
            current_date = datetime.now()
            expiry_dates = []
            
            # For NIFTY/BANKNIFTY - weekly expiries on Thursdays
            # Find next 8 Thursdays (about 2 months worth)
            for i in range(8):
                # Find Thursday of current week + i weeks
                days_ahead = (3 - current_date.weekday()) % 7  # Thursday is 3
                if days_ahead == 0 and current_date.hour > 15:  # After market close
                    days_ahead = 7
                
                next_thursday = current_date + timedelta(days=days_ahead + (i * 7))
                expiry_date = next_thursday.strftime('%Y-%m-%d')
                expiry_dates.append(expiry_date)
            
            # Add monthly expiry (last Thursday of current and next month)
            for month_offset in [0, 1]:
                # Calculate last Thursday of the month
                if month_offset == 0:
                    target_month = current_date.month
                    target_year = current_date.year
                else:
                    if current_date.month == 12:
                        target_month = 1
                        target_year = current_date.year + 1
                    else:
                        target_month = current_date.month + 1
                        target_year = current_date.year
                
                # Last day of the month
                if target_month == 12:
                    last_day = datetime(target_year + 1, 1, 1) - timedelta(days=1)
                else:
                    last_day = datetime(target_year, target_month + 1, 1) - timedelta(days=1)
                
                # Find last Thursday
                while last_day.weekday() != 3:  # Thursday is 3
                    last_day -= timedelta(days=1)
                
                monthly_expiry = last_day.strftime('%Y-%m-%d')
                if monthly_expiry not in expiry_dates:
                    expiry_dates.append(monthly_expiry)
            
            # Sort dates and remove duplicates
            expiry_dates = sorted(list(set(expiry_dates)))
            
            # Convert to DD-MMM-YYYY format for consistency
            formatted_dates = []
            for date_str in expiry_dates:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%d-%b-%Y')
                    formatted_dates.append(formatted_date)
                except:
                    continue
            
            print(f"📅 Calculated {len(formatted_dates)} expiry dates for {instrument}")
            return formatted_dates[:10]  # Return first 10 expiry dates
            
        except Exception as e:
            print(f"❌ Error calculating expiry dates: {e}")
            return []
    
    def _get_next_expiry(self):
        """Get the next expiry date in YYYY-MM-DD format"""
        try:
            current_date = datetime.now()
            days_ahead = (3 - current_date.weekday()) % 7  # Thursday is 3
            if days_ahead == 0 and current_date.hour > 15:  # After market close
                days_ahead = 7
            
            next_thursday = current_date + timedelta(days=days_ahead)
            return next_thursday.strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
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
        """Test DhanHQ API connection using Market Quote API"""
        if not self.client_id or not self.access_token:
            return False, "Client ID or Access Token not provided"
        
        try:
            # Test with NIFTY using Market Quote API
            request_body = {"IDX_I": [13]}  # NIFTY 50 index
            url = f"{self.base_url}/marketfeed/ltp"
            
            response = requests.post(url, headers=self.headers, json=request_body)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'data' in data:
                    nifty_data = data['data'].get('IDX_I', {}).get('13', {})
                    if 'last_price' in nifty_data:
                        price = nifty_data['last_price']
                        return True, f"Connection successful. NIFTY: ₹{price}"
            
            return False, f"Connection failed. Status: {response.status_code}, Response: {response.text}"
                
        except Exception as e:
            return False, f"Connection failed: {e}"
    
    def get_historical_data_batch(self, instruments, period='1y'):
        """Batch fetch historical data for multiple instruments.
        charts/historical endpoint is single-instrument; we loop with rate limiting.
        Returns dict { SYMBOL: DataFrame or None }.
        """
        results = {}
        for sym in instruments:
            try:
                results[sym.upper()] = self.get_historical_data(sym, period)
            except Exception as e:
                print(f"❌ Historical batch error for {sym}: {e}")
                results[sym.upper()] = None
        return results


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


def get_dhan_prices(instruments):
    """Helper batch function to get multiple prices."""
    return dhan_api.get_current_prices(instruments)


def get_dhan_ohlc_batch(instruments):
    """Helper batch function to get multiple OHLC datasets."""
    return dhan_api.get_ohlc_data_batch(instruments)


def get_dhan_historical_batch(instruments, period='1y'):
    """Helper to batch fetch historical datasets."""
    return dhan_api.get_historical_data_batch(instruments, period)
