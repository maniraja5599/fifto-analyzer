"""
Enhanced Market Data Module - Multi-Source Integration
=====================================================

This module provides a robust market data fetching system with multiple sources:
1. DhanHQ API (Primary source)
2. NSE Direct API (Alternative source)
3. Yahoo Finance NSE data (Backup source)
4. Static fallback data (Last resort)

Features:
- Automatic failover between data sources
- Rate limiting and error handling
- Consistent data format across sources
- Real-time price updates with change calculations
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings

# Import existing modules
try:
    from .market_data import get_market_data as get_dhan_market_data
    DHAN_AVAILABLE = True
except ImportError:
    DHAN_AVAILABLE = False

try:
    from .nse_data import get_nse_market_data, get_alternative_nse_data
    from .nse_enhanced import get_enhanced_nse_data
    NSE_AVAILABLE = True
except ImportError:
    NSE_AVAILABLE = False

logger = logging.getLogger(__name__)

class MultiSourceMarketData:
    """Multi-source market data provider with failover support"""
    
    def __init__(self):
        self.sources = []
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize available data sources in priority order"""
        # Primary source: DhanHQ
        if DHAN_AVAILABLE and getattr(settings, 'USE_DHAN_API', False):
            self.sources.append({
                'name': 'DhanHQ',
                'function': get_dhan_market_data,
                'priority': 1
            })
        
        # Alternative source: NSE Direct
        if NSE_AVAILABLE:
            self.sources.append({
                'name': 'NSE_Enhanced',
                'function': get_enhanced_nse_data,
                'priority': 2
            })
            
            self.sources.append({
                'name': 'NSE_Direct',
                'function': get_nse_market_data,
                'priority': 3
            })
            
            # Backup source: NSE via Yahoo Finance
            self.sources.append({
                'name': 'NSE_Yahoo',
                'function': get_alternative_nse_data,
                'priority': 4
            })
        
        # Last resort: Static fallback
        self.sources.append({
            'name': 'Fallback',
            'function': self._get_static_fallback_data,
            'priority': 5
        })
    
    def get_market_data(self, force_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Get market data with automatic failover
        
        Args:
            force_source: Force use of specific source ('DhanHQ', 'NSE_Direct', 'NSE_Yahoo', 'Fallback')
            
        Returns:
            Dict with market data for NIFTY and BANKNIFTY
        """
        if force_source:
            return self._get_data_from_source(force_source)
        
        # Try sources in priority order
        for source in sorted(self.sources, key=lambda x: x['priority']):
            try:
                logger.info(f"🔄 Trying {source['name']} for market data...")
                data = source['function']()
                
                if self._validate_data(data):
                    logger.info(f"✅ Successfully fetched data from {source['name']}")
                    self._add_source_info(data, source['name'])
                    return data
                else:
                    logger.warning(f"⚠️ Invalid data from {source['name']}")
                    
            except Exception as e:
                logger.error(f"❌ {source['name']} failed: {str(e)}")
                continue
        
        # If all sources fail, return minimal fallback
        logger.error("🚨 All data sources failed!")
        return self._get_emergency_fallback()
    
    def _get_data_from_source(self, source_name: str) -> Dict[str, Any]:
        """Get data from a specific source"""
        for source in self.sources:
            if source['name'] == source_name:
                try:
                    data = source['function']()
                    self._add_source_info(data, source_name)
                    return data
                except Exception as e:
                    logger.error(f"Error from {source_name}: {str(e)}")
                    return self._get_emergency_fallback()
        
        logger.error(f"Unknown source: {source_name}")
        return self._get_emergency_fallback()
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate that data contains required information"""
        if not isinstance(data, dict):
            return False
        
        required_symbols = ['NIFTY', 'BANKNIFTY']
        required_fields = ['price', 'change', 'change_percent']
        
        for symbol in required_symbols:
            if symbol not in data:
                return False
            
            symbol_data = data[symbol]
            if not isinstance(symbol_data, dict):
                return False
            
            for field in required_fields:
                if field not in symbol_data:
                    return False
                
                # Check if price is reasonable (not zero or negative)
                if field == 'price' and symbol_data[field] <= 0:
                    return False
        
        return True
    
    def _add_source_info(self, data: Dict[str, Any], source_name: str):
        """Add source information to data"""
        for symbol in data:
            if isinstance(data[symbol], dict):
                data[symbol]['data_source'] = source_name
                data[symbol]['fetch_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _get_static_fallback_data(self) -> Dict[str, Any]:
        """Static fallback data for when all APIs fail"""
        current_time = datetime.now().strftime('%H:%M:%S')
        
        return {
            'NIFTY': {
                'price': 24500.00,
                'change': 125.50,
                'change_percent': 0.51,
                'previous_close': 24374.50,
                'status': 'positive',
                'last_updated': current_time,
                'source': 'Static_Fallback',
                'open': 24400.00,
                'high': 24550.00,
                'low': 24350.00
            },
            'BANKNIFTY': {
                'price': 51200.00,
                'change': -80.25,
                'change_percent': -0.16,
                'previous_close': 51280.25,
                'status': 'negative',
                'last_updated': current_time,
                'source': 'Static_Fallback',
                'open': 51300.00,
                'high': 51350.00,
                'low': 51150.00
            }
        }
    
    def _get_emergency_fallback(self) -> Dict[str, Any]:
        """Emergency fallback with minimal data"""
        current_time = datetime.now().strftime('%H:%M:%S')
        
        return {
            'NIFTY': {
                'price': 0,
                'change': 0,
                'change_percent': 0,
                'previous_close': 0,
                'status': 'neutral',
                'last_updated': current_time,
                'source': 'Emergency_Fallback',
                'error': 'All data sources failed'
            },
            'BANKNIFTY': {
                'price': 0,
                'change': 0,
                'change_percent': 0,
                'previous_close': 0,
                'status': 'neutral',
                'last_updated': current_time,
                'source': 'Emergency_Fallback',
                'error': 'All data sources failed'
            }
        }
    
    def get_available_sources(self) -> list:
        """Get list of available data sources"""
        return [source['name'] for source in self.sources]
    
    def test_all_sources(self) -> Dict[str, Any]:
        """Test all available sources and return results"""
        results = {}
        
        for source in self.sources:
            try:
                logger.info(f"🧪 Testing {source['name']}...")
                data = source['function']()
                
                if self._validate_data(data):
                    results[source['name']] = {
                        'status': 'success',
                        'data': data,
                        'nifty_price': data.get('NIFTY', {}).get('price', 0),
                        'banknifty_price': data.get('BANKNIFTY', {}).get('price', 0)
                    }
                else:
                    results[source['name']] = {
                        'status': 'invalid_data',
                        'data': data
                    }
                    
            except Exception as e:
                results[source['name']] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results

# Global instance for easy access
market_data_provider = MultiSourceMarketData()

def get_enhanced_market_data(force_source: Optional[str] = None) -> Dict[str, Any]:
    """
    Get enhanced market data with multi-source support
    
    Args:
        force_source: Optional source to force use ('DhanHQ', 'NSE_Direct', 'NSE_Yahoo', 'Fallback')
        
    Returns:
        Market data dictionary with NIFTY and BANKNIFTY information
    """
    return market_data_provider.get_market_data(force_source)

def test_data_sources() -> Dict[str, Any]:
    """Test all available data sources"""
    return market_data_provider.test_all_sources()

def get_available_data_sources() -> list:
    """Get list of available data sources"""
    return market_data_provider.get_available_sources()

# Backward compatibility function
def get_market_data_with_nse_fallback() -> Dict[str, Any]:
    """
    Get market data with NSE as fallback (backward compatibility)
    This maintains the existing function signature while adding NSE support
    """
    return get_enhanced_market_data()
