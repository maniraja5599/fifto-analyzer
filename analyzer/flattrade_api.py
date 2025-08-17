# analyzer/flattrade_api.py - Official FlatTrade API Implementation

import requests
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlencode, urlparse

logger = logging.getLogger(__name__)

class FlatTradeAPI:
    """
    Official                 return {
                    'success': True,
                    'message': 'Connection successful',
                    'client_id': result.get('actid', self.client_id),
                    'broker_name': result.get('brkname', 'FlatTrade'),
                    'user_type': result.get('uprev', 'N/A')
                }de API implementation based on pi.flattrade.in/docs
    """
    
    # Base URLs
    AUTH_URL = "https://auth.flattrade.in"
    API_BASE_URL = "https://piconnect.flattrade.in/PiConnectTP"
    TOKEN_URL = "https://authapi.flattrade.in/trade/apitoken"
    # Alternative token URL for testing
    TOKEN_URL_ALT = "https://authapi.flattrade.in/auth/token"
    
    def __init__(self, api_key: str, api_secret: str, client_id: Optional[str] = None):
        """
        Initialize FlatTrade API client
        
        Args:
            api_key: FlatTrade API Key
            api_secret: FlatTrade API Secret
            client_id: FlatTrade Client ID (UCC)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.client_id = client_id or api_key  # Client ID can be same as API key
        self.access_token = None
        self.session = requests.Session()
        
    @classmethod
    def generate_oauth_url(cls, api_key: str, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate FlatTrade OAuth URL for authentication
        
        Args:
            api_key: FlatTrade API Key
            redirect_uri: Callback URL after authentication
            state: Optional state parameter to preserve client_id
            
        Returns:
            OAuth authorization URL
        """
        params = {
            'app_key': api_key,
            'redirect_uri': redirect_uri,
            'response_type': 'code'
        }
        
        if state:
            params['state'] = state
        
        # Using the direct auth URL format from documentation
        oauth_url = f"{cls.AUTH_URL}/?{urlencode(params)}"
        logger.info(f"Generated FlatTrade OAuth URL: {oauth_url}")
        return oauth_url
    
    @classmethod
    def exchange_auth_code(cls, request_code: str, api_key: str, api_secret: str) -> Tuple[bool, Dict]:
        """
        Exchange authorization code for access token
        
        Args:
            request_code: Authorization code from callback
            api_key: FlatTrade API Key
            api_secret: FlatTrade API Secret
            
        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Create SHA-256 hash as per FlatTrade documentation
            # Format: SHA-256 hash of (api_key + request_code + api_secret)
            hash_string = f"{api_key}{request_code}{api_secret}"
            checksum = hashlib.sha256(hash_string.encode()).hexdigest()
            
            logger.info(f"Exchanging auth code for token with API key: {api_key[:10]}...")
            logger.info(f"Hash string length: {len(hash_string)}, Checksum: {checksum[:20]}...")
            
            # Try multiple endpoint and payload variations
            variations = [
                # Original format with form data
                {
                    'url': cls.TOKEN_URL,
                    'payload': {
                        'api_key': api_key,
                        'request_code': request_code,
                        'api_secret': checksum
                    },
                    'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                    'method': 'form'
                },
                # JSON format
                {
                    'url': cls.TOKEN_URL,
                    'payload': {
                        'api_key': api_key,
                        'request_code': request_code,
                        'api_secret': checksum
                    },
                    'headers': {'Content-Type': 'application/json'},
                    'method': 'json'
                },
                # Alternative field names
                {
                    'url': cls.TOKEN_URL,
                    'payload': {
                        'apikey': api_key,
                        'requestcode': request_code,
                        'apisecret': checksum
                    },
                    'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                    'method': 'form'
                },
                # Try different endpoint
                {
                    'url': "https://authapi.flattrade.in/auth/api_token",
                    'payload': {
                        'api_key': api_key,
                        'request_code': request_code,
                        'api_secret': checksum
                    },
                    'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                    'method': 'form'
                },
                # Try yet another endpoint
                {
                    'url': "https://piconnect.flattrade.in/PiConnectTP/TokenGenerate",
                    'payload': {
                        'api_key': api_key,
                        'request_code': request_code,
                        'api_secret': checksum
                    },
                    'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                    'method': 'form'
                }
            ]
            
            for i, variation in enumerate(variations):
                logger.info(f"Trying variation {i+1}: {variation['url']}")
                
                try:
                    if variation['method'] == 'json':
                        response = requests.post(
                            variation['url'], 
                            json=variation['payload'], 
                            headers=variation['headers'],
                            timeout=30
                        )
                    else:
                        response = requests.post(
                            variation['url'], 
                            data=variation['payload'], 
                            headers=variation['headers'],
                            timeout=30
                        )
                    
                    logger.info(f"Variation {i+1} - Status: {response.status_code}")
                    logger.info(f"Variation {i+1} - Headers: {dict(response.headers)}")
                    logger.info(f"Variation {i+1} - Response: {response.text[:200]}...")
                    
                    # If we get a non-empty response, try to parse it
                    if response.text.strip():
                        try:
                            response_data = response.json()
                            logger.info(f"Variation {i+1} - Parsed JSON: {response_data}")
                            
                            # Check for various success indicators
                            if (response.status_code == 200 and 
                                (response_data.get('status') == 'Ok' or 
                                 response_data.get('stat') == 'Ok' or
                                 'token' in response_data)):
                                
                                token = response_data.get('token') or response_data.get('access_token')
                                client_id = response_data.get('client') or response_data.get('actid') or api_key
                                
                                logger.info(f"✅ Token exchange successful with variation {i+1}")
                                return True, {
                                    'access_token': token,
                                    'client_id': client_id,
                                    'expires_at': datetime.now() + timedelta(hours=24)
                                }
                            
                        except json.JSONDecodeError:
                            # Not JSON, check if it's a plain text response
                            if response.status_code == 200 and len(response.text) > 10:
                                logger.info(f"Variation {i+1} - Got non-JSON response, treating as token")
                                return True, {
                                    'access_token': response.text.strip(),
                                    'client_id': api_key,
                                    'expires_at': datetime.now() + timedelta(hours=24)
                                }
                    
                except requests.RequestException as req_e:
                    logger.warning(f"Variation {i+1} request failed: {req_e}")
                    continue
            
            logger.error("All token exchange variations failed")
            return False, {'error': 'All authentication methods failed - please check FlatTrade API documentation'}
                
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return False, {'error': f'Exchange error: {str(e)}'}
    
    def set_access_token(self, token: str):
        """Set access token for API calls"""
        self.access_token = token
        logger.info(f"Access token set: {token[:10]}...")
    
    def _make_request(self, endpoint: str, data: Dict) -> Tuple[bool, Dict]:
        """
        Make authenticated API request to FlatTrade
        
        Args:
            endpoint: API endpoint path
            data: Request data (will be sent as jData)
            
        Returns:
            Tuple of (success, response_data)
        """
        if not self.access_token:
            return False, {'error': 'Access token not set'}
        
        try:
            url = f"{self.API_BASE_URL}/{endpoint}"
            
            # Prepare payload as per FlatTrade API format
            payload = {
                'jData': json.dumps(data),
                'jKey': self.access_token
            }
            
            logger.debug(f"Making request to {url} with data: {data}")
            
            response = self.session.post(url, data=payload, timeout=30)
            
            # Enhanced error logging for debugging
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} error on {endpoint}")
                logger.error(f"Request URL: {url}")
                logger.error(f"Request Data: {data}")
                logger.error(f"Response Text: {response.text}")
                logger.error(f"Response Headers: {dict(response.headers)}")
                return False, {'error': f'HTTP {response.status_code}: {response.text}'}
            
            response_data = response.json()
            logger.debug(f"Response from {endpoint}: {response_data}")
            
            # Check for API-level errors
            if isinstance(response_data, dict) and response_data.get('stat') == 'Not_Ok':
                error_msg = response_data.get('emsg', 'Unknown API error')
                logger.error(f"FlatTrade API error on {endpoint}: {error_msg}")
                logger.error(f"Full response: {response_data}")
                return False, {'error': error_msg, 'full_response': response_data}
            
            return True, response_data
                
        except requests.RequestException as e:
            logger.error(f"Request failed on {endpoint}: {e}")
            return False, {'error': f'Network error: {str(e)}'}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error on {endpoint}: {e}")
            return False, {'error': f'Invalid response format: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected error on {endpoint}: {e}")
            return False, {'error': f'Request error: {str(e)}'}
    
    def get_user_details(self) -> Tuple[bool, Dict]:
        """Get user details and account information"""
        data = {'uid': self.client_id}
        return self._make_request('UserDetails', data)
    
    def get_limits(self) -> Tuple[bool, Dict]:
        """Get account limits and margin information"""
        data = {
            'uid': self.client_id,
            'actid': self.client_id
        }
        return self._make_request('Limits', data)
    
    def get_positions(self) -> Tuple[bool, Dict]:
        """Get positions book"""
        data = {
            'uid': self.client_id,
            'actid': self.client_id
        }
        return self._make_request('PositionBook', data)
    
    def get_orderbook(self) -> Tuple[bool, Dict]:
        """Get order book"""
        data = {'uid': self.client_id}
        return self._make_request('OrderBook', data)
    
    def get_tradebook(self) -> Tuple[bool, Dict]:
        """Get trade book"""
        data = {
            'uid': self.client_id,
            'actid': self.client_id
        }
        return self._make_request('TradeBook', data)
    
    def get_holdings(self, product: str = 'C') -> Tuple[bool, Dict]:
        """Get holdings"""
        data = {
            'uid': self.client_id,
            'actid': self.client_id,
            'prd': product
        }
        return self._make_request('Holdings', data)
    
    def place_order(self, 
                   symbol: str,
                   exchange: str,
                   transaction_type: str,  # 'B' for BUY, 'S' for SELL
                   quantity: int,
                   price: float,
                   product: str = 'M',  # M=NRML, I=MIS, C=CNC, H=CO, B=BO
                   order_type: str = 'LMT',  # LMT, MKT, SL-LMT, SL-MKT
                   validity: str = 'DAY',  # DAY, IOC, EOS
                   disclosed_quantity: int = 0,
                   trigger_price: Optional[float] = None,
                   remarks: str = '',
                   amo: bool = False) -> Tuple[bool, Dict]:
        """
        Place order on FlatTrade
        
        Args:
            symbol: Trading symbol (e.g., 'NIFTY2312525000CE')
            exchange: Exchange name (e.g., 'NFO', 'NSE')
            transaction_type: 'B' for BUY, 'S' for SELL
            quantity: Order quantity
            price: Order price
            product: Product type (M=NRML, I=MIS, C=CNC, H=CO, B=BO)
            order_type: Order type (LMT, MKT, SL-LMT, SL-MKT)
            validity: Order validity (DAY, IOC, EOS)
            disclosed_quantity: Disclosed quantity
            trigger_price: Trigger price for SL orders
            remarks: Order remarks
            amo: After Market Order flag
            
        Returns:
            Tuple of (success, response_data)
        """
        # Validate required parameters
        if not symbol or not exchange or not transaction_type:
            error_msg = f"Missing required parameters: symbol={symbol}, exchange={exchange}, transaction_type={transaction_type}"
            logger.error(error_msg)
            return False, {'error': error_msg}
        
        if quantity <= 0:
            error_msg = f"Invalid quantity: {quantity}"
            logger.error(error_msg)
            return False, {'error': error_msg}
        
        if order_type in ['LMT', 'SL-LMT'] and price <= 0:
            error_msg = f"Invalid price for limit order: {price}"
            logger.error(error_msg)
            return False, {'error': error_msg}
        
        # Log order details for debugging
        logger.info(f"FlatTrade placing order: {transaction_type} {quantity} {symbol} @ {price} on {exchange}")
        
        data = {
            'uid': self.client_id,
            'actid': self.client_id,
            'exch': exchange,
            'tsym': symbol,
            'qty': str(quantity),
            'prc': str(price) if price > 0 else '0',
            'prd': product,
            'trantype': transaction_type,
            'prctyp': order_type,
            'ret': validity,
            'dscqty': str(disclosed_quantity),
            'ordersource': 'API'
        }
        
        if trigger_price and trigger_price > 0:
            data['trgprc'] = str(trigger_price)
            
        if remarks:
            data['remarks'] = remarks[:50]  # Limit remarks length
            
        if amo:
            data['amo'] = 'Yes'
        
        # Log the exact data being sent
        logger.info(f"FlatTrade order data: {data}")
            
        return self._make_request('PlaceOrder', data)
    
    def modify_order(self,
                    order_id: str,
                    exchange: str,
                    symbol: str,
                    quantity: int,
                    price: float,
                    order_type: str = 'LMT',
                    validity: str = 'DAY',
                    trigger_price: Optional[float] = None) -> Tuple[bool, Dict]:
        """Modify existing order"""
        data = {
            'uid': self.client_id,
            'norenordno': order_id,
            'exch': exchange,
            'tsym': symbol,
            'qty': str(quantity),
            'prc': str(price),
            'prctyp': order_type,
            'ret': validity
        }
        
        if trigger_price:
            data['trgprc'] = str(trigger_price)
            
        return self._make_request('ModifyOrder', data)
    
    def cancel_order(self, order_id: str) -> Tuple[bool, Dict]:
        """Cancel order"""
        data = {
            'uid': self.client_id,
            'norenordno': order_id
        }
        return self._make_request('CancelOrder', data)
    
    def get_quotes(self, exchange: str, token: str) -> Tuple[bool, Dict]:
        """Get quotes for a symbol"""
        data = {
            'uid': self.client_id,
            'exch': exchange,
            'token': token
        }
        return self._make_request('GetQuotes', data)
    
    def search_scrips(self, search_text: str, exchange: Optional[str] = None) -> Tuple[bool, Dict]:
        """Search for trading symbols"""
        data = {
            'uid': self.client_id,
            'stext': search_text
        }
        
        if exchange:
            data['exch'] = exchange
            
        return self._make_request('SearchScrip', data)
    
    def get_option_chain(self, symbol: str, exchange: str, strike_price: str, count: int = 10) -> Tuple[bool, Dict]:
        """Get option chain data"""
        data = {
            'uid': self.client_id,
            'tsym': symbol,
            'exch': exchange,
            'strprc': strike_price,
            'cnt': str(count)
        }
        return self._make_request('GetOptionChain', data)
    
    def test_connection(self) -> Dict:
        """Test API connection"""
        try:
            if not self.access_token:
                return {
                    'success': False,
                    'error': 'No access token available',
                    'message': 'Please complete OAuth authentication first'
                }
            
            # Test with user details call
            success, result = self.get_user_details()
            
            if success:
                return {
                    'success': True,
                    'message': 'FlatTrade API connection successful',
                    'account_id': result.get('actid', self.client_id),
                    'broker_name': result.get('brkname', 'FlatTrade'),
                    'user_type': result.get('uprev', 'N/A')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Connection test failed'),
                    'message': 'Unable to connect to FlatTrade API'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Connection test failed with exception'
            }


# Convenience class for broker integration
class FlatTradeBrokerHandler:
    """Wrapper class for FlatTrade broker integration"""
    
    def __init__(self, config: Dict):
        """
        Initialize with broker configuration
        
        Args:
            config: Dict containing api_key, api_secret, client_id, access_token
        """
        self.config = config
        self.api = FlatTradeAPI(
            api_key=config.get('api_key', ''),
            api_secret=config.get('api_secret', config.get('secret_key', '')),
            client_id=config.get('client_id', config.get('api_key', ''))  # client_id is same as api_key in FlatTrade
        )
        
        # Set access token if available
        access_token = config.get('access_token')
        if access_token:
            self.api.set_access_token(access_token)
    
    @classmethod
    def generate_oauth_url(cls, api_key: str, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate OAuth URL"""
        return FlatTradeAPI.generate_oauth_url(api_key, redirect_uri, state)
    
    @classmethod
    def exchange_auth_code(cls, request_code: str, api_key: str, api_secret: str, redirect_uri: Optional[str] = None) -> Tuple[bool, Dict]:
        """Exchange auth code for token"""
        return FlatTradeAPI.exchange_auth_code(request_code, api_key, api_secret)
    
    def test_connection(self) -> Dict:
        """Test connection"""
        return self.api.test_connection()
    
    def get_positions(self) -> Tuple[bool, List[Dict]]:
        """Get formatted positions"""
        success, result = self.api.get_positions()
        
        if not success:
            return False, []
        
        positions = []
        if isinstance(result, list):
            for pos in result:
                if pos.get('stat') == 'Ok':
                    positions.append({
                        'symbol': pos.get('tsym', ''),
                        'exchange': pos.get('exch', ''),
                        'product': pos.get('prd', ''),
                        'quantity': int(pos.get('netqty', 0)),
                        'average_price': float(pos.get('netavgprc', 0)),
                        'ltp': float(pos.get('lp', 0)),
                        'pnl': float(pos.get('rpnl', 0)),
                        'unrealized_pnl': float(pos.get('urmtom', 0))
                    })
        
        return True, positions
    
    def place_order(self, order_params: Dict) -> Tuple[bool, Dict]:
        """Place order with standardized parameters"""
        try:
            # Map standard parameters to FlatTrade format
            symbol = order_params.get('symbol', '')
            exchange = order_params.get('exchange', 'NFO')
            side = 'B' if order_params.get('side', '').upper() == 'BUY' else 'S'
            quantity = int(order_params.get('quantity', 0))
            price = float(order_params.get('price', 0))
            
            # Map product codes
            product_map = {
                'NRML': 'M',
                'MIS': 'I', 
                'CNC': 'C',
                'CO': 'H',
                'BO': 'B'
            }
            product = product_map.get(order_params.get('product', 'NRML'), 'M')
            
            # Map order types
            order_type_map = {
                'LIMIT': 'LMT',
                'MARKET': 'MKT',
                'SL': 'SL-LMT',
                'SL-M': 'SL-MKT'
            }
            order_type = order_type_map.get(order_params.get('order_type', 'LIMIT'), 'LMT')
            
            success, result = self.api.place_order(
                symbol=symbol,
                exchange=exchange,
                transaction_type=side,
                quantity=quantity,
                price=price,
                product=product,
                order_type=order_type,
                trigger_price=order_params.get('trigger_price', 0.0) if order_params.get('trigger_price') else None,
                remarks=order_params.get('tag', '')
            )
            
            if success:
                return True, {
                    'order_id': result.get('norenordno'),
                    'message': 'Order placed successfully'
                }
            else:
                return False, result
                
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            return False, {'error': str(e)}
    
    def get_orderbook(self) -> Tuple[bool, List[Dict]]:
        """Get formatted order book"""
        success, result = self.api.get_orderbook()
        
        if not success:
            return False, []
        
        orders = []
        if isinstance(result, list):
            for order in result:
                if order.get('stat') == 'Ok':
                    orders.append({
                        'order_id': order.get('norenordno', ''),
                        'symbol': order.get('tsym', ''),
                        'exchange': order.get('exch', ''),
                        'side': 'BUY' if order.get('trantype') == 'B' else 'SELL',
                        'quantity': int(order.get('qty', 0)),
                        'price': float(order.get('prc', 0)),
                        'status': order.get('status', ''),
                        'product': order.get('prd', ''),
                        'order_type': order.get('prctyp', ''),
                        'filled_quantity': int(order.get('fillshares', 0)),
                        'average_price': float(order.get('avgprc', 0))
                    })
        
        return True, orders
    
    def place_option_order(self, instrument: str, expiry: str, strike: float,
                          option_type: str, transaction_type: str, quantity: int,
                          order_type: str = 'MARKET') -> Dict:
        """
        Place option order with automatic symbol generation
        
        Args:
            instrument: Index name (NIFTY, BANKNIFTY, etc.)
            expiry: Expiry date in YYYY-MM-DD format
            strike: Strike price
            option_type: CE or PE
            transaction_type: BUY or SELL
            quantity: Order quantity
            order_type: MARKET or LIMIT
            
        Returns:
            Dict with success status and order details
        """
        try:
            # Generate option symbol
            symbol = self._generate_option_symbol(instrument, expiry, strike, option_type)
            
            # Convert transaction type to FlatTrade format
            side = 'B' if transaction_type.upper() == 'BUY' else 'S'
            
            # Convert order type and handle pricing
            ft_order_type = 'MKT' if order_type.upper() == 'MARKET' else 'LMT'
            
            # For market orders, FlatTrade might require a nominal price or specific handling
            if ft_order_type == 'MKT':
                # For market orders, use a nominal price (some brokers require this)
                price = 1.0  # Nominal price for market orders
            else:
                # For limit orders, we need to get actual market price
                # TODO: Implement market price fetching for limit orders
                price = 1.0  # Placeholder - should fetch current market price
            
            logger.info(f"FlatTrade: Placing {ft_order_type} order for {symbol} at price {price}")
            
            success, result = self.api.place_order(
                symbol=symbol,
                exchange='NFO',
                transaction_type=side,
                quantity=quantity,
                price=price,
                product='M',  # NRML
                order_type=ft_order_type,
                validity='DAY'
            )
            
            if success:
                return {
                    'success': True,
                    'order_id': result.get('norenordno'),
                    'message': 'Order placed successfully'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Order placement failed')
                }
                
        except Exception as e:
            logger.error(f"Option order placement error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_option_symbol(self, instrument: str, expiry: str, strike: float, option_type: str) -> str:
        """
        Generate FlatTrade option symbol format
        
        Format examples:
        - NIFTY28AUG25C24650 (Call)
        - BANKNIFTY28AUG25P50000 (Put)
        
        Format: {INSTRUMENT}{DDMMMYY}{C|P}{STRIKE}
        User confirmed format: NIFTY28AUG25C24650
        """
        try:
            from datetime import datetime
            
            # Parse expiry date - handle multiple formats
            expiry_date = None
            
            # Try different date formats that NSE/system might provide
            date_formats = [
                '%d-%b-%Y',      # 21-Aug-2025 (NSE standard format)
                '%Y-%m-%d',      # 2025-08-21
                '%d-%B-%Y',      # 21-August-2025
                '%d-AUG-%Y',     # 21-AUG-2025 (uppercase month)
                '%d-%m-%Y',      # 21-08-2025
                '%Y/%m/%d',      # 2025/08/21
                '%d/%m/%Y',      # 21/08/2025
                '%d%b%Y',        # 21Aug2025
                '%d%B%Y',        # 21August2025
                '%d%b%y',        # 21Aug25
                '%d-%m-%y',      # 21-08-25
                '%y-%m-%d',      # 25-08-21
                '%b %d, %Y',     # Aug 21, 2025
                '%B %d, %Y'      # August 21, 2025
            ]
            
            for fmt in date_formats:
                try:
                    expiry_date = datetime.strptime(expiry, fmt)
                    logger.info(f"FlatTrade: Successfully parsed expiry '{expiry}' using format '{fmt}'")
                    break
                except ValueError:
                    continue
            
            if expiry_date is None:
                # Try to extract date from string if it contains numbers
                import re
                # Try to extract DD-MM-YYYY or DD/MM/YYYY pattern
                date_pattern = r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})'
                match = re.search(date_pattern, expiry)
                if match:
                    day, month, year = match.groups()
                    try:
                        expiry_date = datetime(int(year), int(month), int(day))
                        logger.info(f"FlatTrade: Extracted date from pattern: {expiry}")
                    except:
                        pass
                
                if expiry_date is None:
                    raise ValueError(f"Unable to parse expiry date '{expiry}' with any known format")
            
            # FlatTrade requires DDMMMYY format (e.g., 28AUG25)
            # Using %d%b%y and converting to uppercase to match FlatTrade exactly
            date_str = expiry_date.strftime('%d%b%y').upper()
            
            # Convert option type to FlatTrade format (CE -> C, PE -> P)
            if option_type.upper() in ['CE', 'CALL', 'C']:
                ft_option_type = 'C'
            elif option_type.upper() in ['PE', 'PUT', 'P']:
                ft_option_type = 'P'
            else:
                logger.warning(f"Unknown option type: {option_type}, defaulting to 'C'")
                ft_option_type = 'C'
            
            # Format strike price (remove decimal, ensure integer)
            strike_str = str(int(float(strike)))
            
            # Combine all parts: INSTRUMENT + DATE + OPTION_TYPE + STRIKE
            # Example: NIFTY + 28AUG25 + C + 24650 = NIFTY28AUG25C24650
            symbol = f"{instrument.upper()}{date_str}{ft_option_type}{strike_str}"
            
            logger.info(f"FlatTrade: Generated symbol '{symbol}' from instrument='{instrument}', expiry='{expiry}', strike={strike}, type='{option_type}'")
            return symbol
            
        except Exception as e:
            logger.error(f"FlatTrade symbol generation error: {e}")
            # Enhanced fallback with proper format
            try:
                from datetime import datetime
                # Try to create a basic fallback symbol
                fallback_date = datetime.now().strftime('%d%b%y').upper()
                ft_option_type = 'C' if 'C' in str(option_type).upper() else 'P'
                strike_str = str(int(float(strike)))
                fallback_symbol = f"{instrument.upper()}{fallback_date}{ft_option_type}{strike_str}"
                logger.warning(f"Using fallback symbol: {fallback_symbol}")
                return fallback_symbol
            except:
                # Final fallback
                return f"{instrument}_{expiry}_{int(strike)}_{option_type}"
    
    def get_lot_size(self, instrument: str) -> int:
        """Get lot size for different instruments"""
        lot_sizes = {
            'NIFTY': 75,        # Updated lot sizes as of 2024
            'BANKNIFTY': 15,
            'FINNIFTY': 40,
            'MIDCPNIFTY': 150,
            'SENSEX': 10,
            'BANKEX': 15
        }
        return lot_sizes.get(instrument.upper(), 50)  # Default lot size
