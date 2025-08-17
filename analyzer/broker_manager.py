"""
Live Trading Broker Manager - Multi-Broker Integration
=====================================================

Supports multiple brokers with unified order placement interface:
- DhanHQ (Primary)
- Zerodha Kite API
- Angel Broking API  
- Upstox API
- FlatTrade API (Official Implementation)
- Future: Additional brokers

Features:
- Automatic order placement when analysis is generated
- Target/Stoploss monitoring with auto-close
- Multiple broker account management
- Order types: Market, Limit (default: Market)
- Real-time order status tracking
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.conf import settings
import logging

# Import FlatTrade API implementation
from .flattrade_api import FlatTradeBrokerHandler

logger = logging.getLogger(__name__)

class BrokerOrderManager:
    """Unified order management across multiple brokers"""
    
    def __init__(self):
        self.brokers = {}
        self.active_accounts = []
        self.order_history = []
        self.load_broker_accounts()
        
    def load_broker_accounts(self):
        """Load broker accounts from settings"""
        try:
            from .utils import load_settings
            settings_data = load_settings()
            self.active_accounts = settings_data.get('broker_accounts', [])
            
            # Initialize broker handlers
            for account in self.active_accounts:
                if account.get('enabled', False):
                    broker_type = account.get('broker')  # Use 'broker' not 'broker_type'
                    if broker_type == 'DHAN':
                        self.brokers[account['account_id']] = DhanBrokerHandler(account)
                    elif broker_type == 'ZERODHA':
                        self.brokers[account['account_id']] = ZerodhaBrokerHandler(account)
                    elif broker_type == 'ANGEL':
                        self.brokers[account['account_id']] = AngelBrokerHandler(account)
                    elif broker_type == 'UPSTOX':
                        self.brokers[account['account_id']] = UpstoxBrokerHandler(account)
                    elif broker_type == 'FLATTRADE':
                        # For FlatTrade, use client_id as the key instead of account_id
                        account_key = account.get('client_id', account.get('account_id'))
                        self.brokers[account_key] = FlatTradeBrokerHandler(account)
                        
        except Exception as e:
            logger.error(f"Error loading broker accounts: {e}")
            
    def place_strategy_orders(self, analysis_data: Dict, account_ids: Optional[List[str]] = None) -> Dict:
        """
        Place orders for complete strategy (CE + PE + Hedge) across multiple accounts
        
        Args:
            analysis_data: Analysis result with strikes and hedge data
            account_ids: List of account IDs to place orders (None = all enabled accounts)
            
        Returns:
            Dict with order placement results
        """
        if account_ids is None:
            # Build account_ids list properly, using client_id for FlatTrade and account_id for others
            account_ids = []
            for acc in self.active_accounts:
                if acc.get('enabled', False):
                    if acc.get('broker') == 'FLATTRADE':
                        account_ids.append(acc.get('client_id'))
                    else:
                        account_ids.append(acc.get('account_id'))
            
        results = {
            'success': True,
            'orders_placed': [],
            'errors': [],
            'total_accounts': len(account_ids),
            'successful_accounts': 0
        }
        
        try:
            # Extract strategy data
            instrument = analysis_data.get('instrument', 'NIFTY')
            expiry = analysis_data.get('expiry', '')
            df_data = analysis_data.get('df_data', [])
            
            if not df_data:
                results['success'] = False
                results['errors'].append("No strategy data found in analysis")
                return results
                
            if not expiry:
                results['success'] = False
                results['errors'].append("No expiry date found in analysis")
                return results
                
            # Place orders for each entry in analysis
            for entry in df_data:
                entry_results = self._place_entry_orders(entry, instrument, expiry, account_ids or [])
                results['orders_placed'].extend(entry_results['orders'])
                results['errors'].extend(entry_results['errors'])
                
            results['successful_accounts'] = len([acc for acc in account_ids if acc in [o['account_id'] for o in results['orders_placed']]])
            
        except Exception as e:
            logger.error(f"Error placing strategy orders: {e}")
            results['success'] = False
            results['errors'].append(f"Strategy order error: {e}")
            
        return results
        
    def _place_entry_orders(self, entry: Dict, instrument: str, expiry: str, account_ids: List[str]) -> Dict:
        """Place orders for a single entry (CE + PE + Hedge)"""
        results = {'orders': [], 'errors': []}
        
        # Extract entry data
        ce_strike = entry.get('CE Strike')
        pe_strike = entry.get('PE Strike')
        ce_hedge_strike = entry.get('CE Hedge Strike')
        pe_hedge_strike = entry.get('PE Hedge Strike')
        
        for account_id in account_ids:
            if account_id not in self.brokers:
                results['errors'].append(f"Broker handler not found for account {account_id}")
                continue
                
            broker = self.brokers[account_id]
            
            try:
                # 1. Sell CE Option
                if ce_strike:
                    ce_order = broker.place_option_order(
                        instrument=instrument,
                        expiry=expiry,
                        strike=ce_strike,
                        option_type='CE',
                        transaction_type='SELL',
                        quantity=broker.get_lot_size(instrument),
                        order_type='MARKET'
                    )
                    if ce_order['success']:
                        results['orders'].append({
                            'account_id': account_id,
                            'order_id': ce_order['order_id'],
                            'type': 'MAIN_CE',
                            'instrument': instrument,
                            'strike': ce_strike,
                            'option_type': 'CE',
                            'transaction': 'SELL',
                            'status': 'PLACED'
                        })
                        
                # 2. Sell PE Option  
                if pe_strike:
                    pe_order = broker.place_option_order(
                        instrument=instrument,
                        expiry=expiry,
                        strike=pe_strike,
                        option_type='PE',
                        transaction_type='SELL',
                        quantity=broker.get_lot_size(instrument),
                        order_type='MARKET'
                    )
                    if pe_order['success']:
                        results['orders'].append({
                            'account_id': account_id,
                            'order_id': pe_order['order_id'],
                            'type': 'MAIN_PE',
                            'instrument': instrument,
                            'strike': pe_strike,
                            'option_type': 'PE',
                            'transaction': 'SELL',
                            'status': 'PLACED'
                        })
                        
                # 3. Buy CE Hedge
                if ce_hedge_strike:
                    ce_hedge_order = broker.place_option_order(
                        instrument=instrument,
                        expiry=expiry,
                        strike=ce_hedge_strike,
                        option_type='CE',
                        transaction_type='BUY',
                        quantity=broker.get_lot_size(instrument),
                        order_type='MARKET'
                    )
                    if ce_hedge_order['success']:
                        results['orders'].append({
                            'account_id': account_id,
                            'order_id': ce_hedge_order['order_id'],
                            'type': 'HEDGE_CE',
                            'instrument': instrument,
                            'strike': ce_hedge_strike,
                            'option_type': 'CE',
                            'transaction': 'BUY',
                            'status': 'PLACED'
                        })
                        
                # 4. Buy PE Hedge
                if pe_hedge_strike:
                    pe_hedge_order = broker.place_option_order(
                        instrument=instrument,
                        expiry=expiry,
                        strike=pe_hedge_strike,
                        option_type='PE',
                        transaction_type='BUY',
                        quantity=broker.get_lot_size(instrument),
                        order_type='MARKET'
                    )
                    if pe_hedge_order['success']:
                        results['orders'].append({
                            'account_id': account_id,
                            'order_id': pe_hedge_order['order_id'],
                            'type': 'HEDGE_PE',
                            'instrument': instrument,
                            'strike': pe_hedge_strike,
                            'option_type': 'PE',
                            'transaction': 'BUY',
                            'status': 'PLACED'
                        })
                        
            except Exception as e:
                results['errors'].append(f"Error placing orders for account {account_id}: {e}")
                
        return results
        
    def monitor_and_close_positions(self, trade_data: Dict) -> Dict:
        """Monitor positions and auto-close on target/stoploss"""
        results = {
            'closed_positions': [],
            'monitoring_positions': [],
            'errors': []
        }
        
        try:
            target_amount = trade_data.get('target_amount')
            stoploss_amount = trade_data.get('stoploss_amount')
            
            if not target_amount and not stoploss_amount:
                return results
                
            # Get current P&L for the trade
            current_pnl = self._calculate_live_pnl(trade_data)
            
            # Check if target hit
            if target_amount and current_pnl >= target_amount:
                close_result = self._close_all_positions(trade_data, 'TARGET_HIT')
                results['closed_positions'].append(close_result)
                
            # Check if stoploss hit
            elif stoploss_amount and current_pnl <= -stoploss_amount:
                close_result = self._close_all_positions(trade_data, 'STOPLOSS_HIT')
                results['closed_positions'].append(close_result)
                
            else:
                results['monitoring_positions'].append({
                    'trade_id': trade_data.get('id'),
                    'current_pnl': current_pnl,
                    'target': target_amount,
                    'stoploss': stoploss_amount
                })
                
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            results['errors'].append(f"Monitoring error: {e}")
            
        return results
        
    def _calculate_live_pnl(self, trade_data: Dict) -> float:
        """Calculate live P&L from broker positions"""
        # Implementation depends on broker APIs
        # This is a placeholder - actual implementation would fetch live positions
        return 0.0
        
    def _close_all_positions(self, trade_data: Dict, reason: str) -> Dict:
        """Close all positions for a trade across all accounts"""
        close_results = {
            'trade_id': trade_data.get('id'),
            'reason': reason,
            'closed_orders': [],
            'errors': []
        }
        
        # Implementation would close all positions
        # This is a placeholder for the actual closing logic
        
        return close_results


class DhanBrokerHandler:
    """DhanHQ Broker Implementation"""
    
    def __init__(self, account_config: Dict):
        self.account_id = account_config['account_id']
        self.client_id = account_config.get('client_id')
        self.access_token = account_config.get('access_token')
        self.base_url = "https://api.dhan.co/v2"
        
        self.headers = {
            'access-token': self.access_token,
            'client-id': self.client_id,
            'Content-Type': 'application/json'
        }
        
    def place_option_order(self, instrument: str, expiry: str, strike: float, 
                          option_type: str, transaction_type: str, quantity: int,
                          order_type: str = 'MARKET') -> Dict:
        """Place option order via DhanHQ API"""
        try:
            # Convert parameters to DhanHQ format
            order_data = {
                "dhanClientId": self.client_id,
                "correlationId": f"{instrument}_{expiry}_{strike}_{option_type}_{int(time.time())}",
                "transactionType": transaction_type,
                "exchangeSegment": "NSE_FNO",
                "productType": "INTRADAY",
                "orderType": order_type,
                "validity": "DAY",
                "securityId": self._get_option_security_id(instrument, expiry, strike, option_type),
                "quantity": quantity,
                "disclosedQuantity": 0,
                "price": 0 if order_type == 'MARKET' else 0,  # Set appropriate price for limit orders
                "triggerPrice": 0
            }
            
            response = requests.post(
                f"{self.base_url}/orders",
                headers=self.headers,
                json=order_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'order_id': result.get('orderId'),
                    'message': 'Order placed successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f"Order failed: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Order placement error: {e}"
            }
            
    def _get_option_security_id(self, instrument: str, expiry: str, strike: float, option_type: str) -> str:
        """Get DhanHQ security ID for option contract"""
        # This would need to be implemented based on DhanHQ's security ID mapping
        # For now, return a placeholder
        return f"{instrument}_{expiry}_{strike}_{option_type}"
        
    def get_lot_size(self, instrument: str) -> int:
        """Get lot size for instrument"""
        lot_sizes = {
            'NIFTY': 75,
            'BANKNIFTY': 15,
            'SENSEX': 10
        }
        return lot_sizes.get(instrument, 50)


class ZerodhaBrokerHandler:
    """Zerodha Kite API Implementation"""
    
    def __init__(self, account_config: Dict):
        self.account_id = account_config['account_id']
        self.api_key = account_config.get('api_key')
        self.access_token = account_config.get('access_token')
        # Initialize Kite API client here
        
    def place_option_order(self, instrument: str, expiry: str, strike: float,
                          option_type: str, transaction_type: str, quantity: int,
                          order_type: str = 'MARKET') -> Dict:
        """Place option order via Kite API"""
        # Implementation for Zerodha Kite API
        return {'success': False, 'error': 'Zerodha integration pending'}
        
    def get_lot_size(self, instrument: str) -> int:
        """Get lot size for instrument"""
        lot_sizes = {
            'NIFTY': 75,
            'BANKNIFTY': 15,
            'SENSEX': 10
        }
        return lot_sizes.get(instrument, 50)


class AngelBrokerHandler:
    """Angel Broking API Implementation"""
    
    def __init__(self, account_config: Dict):
        self.account_id = account_config['account_id']
        self.api_key = account_config.get('api_key')
        self.access_token = account_config.get('access_token')
        
    def place_option_order(self, instrument: str, expiry: str, strike: float,
                          option_type: str, transaction_type: str, quantity: int,
                          order_type: str = 'MARKET') -> Dict:
        """Place option order via Angel API"""
        # Implementation for Angel Broking API
        return {'success': False, 'error': 'Angel Broking integration pending'}
        
    def get_lot_size(self, instrument: str) -> int:
        """Get lot size for instrument"""
        lot_sizes = {
            'NIFTY': 75,
            'BANKNIFTY': 15,
            'SENSEX': 10
        }
        return lot_sizes.get(instrument, 50)


class UpstoxBrokerHandler:
    """Upstox API Implementation"""
    
    def __init__(self, account_config: Dict):
        self.account_id = account_config['account_id']
        self.api_key = account_config.get('api_key')
        self.access_token = account_config.get('access_token')
        
    def place_option_order(self, instrument: str, expiry: str, strike: float,
                          option_type: str, transaction_type: str, quantity: int,
                          order_type: str = 'MARKET') -> Dict:
        """Place option order via Upstox API"""
        # Implementation for Upstox API
        return {'success': False, 'error': 'Upstox integration pending'}
        
    def get_lot_size(self, instrument: str) -> int:
        """Get lot size for instrument"""
        lot_sizes = {
            'NIFTY': 75,
            'BANKNIFTY': 15,
            'SENSEX': 10
        }
        return lot_sizes.get(instrument, 50)


# Global broker manager instance
broker_manager = BrokerOrderManager()
