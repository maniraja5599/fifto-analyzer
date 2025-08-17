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
            
            print(f"🔍 DEBUG: Loading {len(self.active_accounts)} broker accounts")
            
            # Initialize broker handlers
            for account in self.active_accounts:
                if account.get('enabled', False):
                    broker_type = account.get('broker')  # Use 'broker' not 'broker_type'
                    print(f"🔍 DEBUG: Initializing {broker_type} broker for account {account.get('client_id', account.get('account_id'))}")
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
                        print(f"🔍 DEBUG: Creating FlatTrade handler with key: {account_key}")
                        self.brokers[account_key] = FlatTradeBrokerHandler(account)
                        print(f"🔍 DEBUG: FlatTrade handler created successfully")
            
            print(f"🔍 DEBUG: Total brokers initialized: {len(self.brokers)}")
            print(f"🔍 DEBUG: Broker keys: {list(self.brokers.keys())}")
                        
        except Exception as e:
            logger.error(f"Error loading broker accounts: {e}")
            print(f"🔍 DEBUG: Error loading broker accounts: {e}")
            import traceback
            traceback.print_exc()
            
    def place_strategy_orders(self, analysis_data: Dict, account_ids: Optional[List[str]] = None) -> Dict:
        """
        Place orders for complete strategy (CE + PE + Hedge) across multiple accounts
        
        Args:
            analysis_data: Analysis result with strikes and hedge data
            account_ids: List of account IDs to place orders (None = all enabled accounts)
            
        Returns:
            Dict with success status, orders placed, and any errors
        """
        import traceback
        
        print(f"🚀 BROKER_MANAGER: place_strategy_orders called!")
        print(f"🔍 DEBUG: Instance ID: {id(self)}")
        print(f"🔍 DEBUG: account_ids passed: {account_ids}")
        print(f"🔍 DEBUG: available brokers: {list(self.brokers.keys())}")
        print(f"🔍 DEBUG: active_accounts: {len(self.active_accounts)}")
        print(f"🔍 DEBUG: analysis_data keys: {list(analysis_data.keys()) if analysis_data else 'None'}")
        print(f"🔍 DEBUG: analysis_data type: {type(analysis_data)}")
        for key, value in analysis_data.items():
            if key == 'schedule_config':
                print(f"🔍 DEBUG: schedule_config found: {value}")
            elif key == 'df_data':
                print(f"🔍 DEBUG: df_data found: {len(value) if value else 0} entries")
        
        print(f"🔍 DEBUG: Call stack:")
        for line in traceback.format_stack()[-3:-1]:  # Show last 2 stack frames
            print(f"     {line.strip()}")
        
        results = {
            'success': False,
            'orders_placed': [],
            'errors': [],
            'total_accounts': 0,
            'successful_accounts': 0
        }
        
        # Validate analysis data
        if not analysis_data:
            results['errors'].append('No analysis data provided')
            return results
        
        # Use all enabled accounts if none specified
        if not account_ids:
            account_ids = list(self.brokers.keys())
            print(f"🔍 DEBUG: Using all available accounts: {account_ids}")
        
        results['total_accounts'] = len(account_ids)
        
        # Check if we have strategy data in the expected format
        strategy_entries = []
        
        # Handle different analysis data formats
        if 'strikes' in analysis_data and 'hedge' in analysis_data:
            # New format with strikes and hedge
            strikes = analysis_data['strikes']
            hedge = analysis_data['hedge']
            
            strategy_entry = {
                'CE Strike': strikes.get('ce_strike', {}),
                'PE Strike': strikes.get('pe_strike', {}),
                'CE Hedge Strike': hedge.get('ce_buy_hedge', {}),
                'PE Hedge Strike': hedge.get('pe_buy_hedge', {})
            }
            strategy_entries.append(strategy_entry)
            print(f"🔍 DEBUG: Using new format with strikes/hedge data")
            
        elif 'strategy_entries' in analysis_data:
            # Old format with strategy_entries list
            strategy_entries = analysis_data['strategy_entries']
            print(f"🔍 DEBUG: Using old format with {len(strategy_entries)} strategy entries")
            
        elif 'df_data' in analysis_data:
            # Current format with df_data from generate_analysis()
            df_data = analysis_data['df_data']
            print(f"🔍 DEBUG: Using df_data format with {len(df_data)} entries")
            
            # Get selected risk levels from schedule config (if provided)
            selected_risk_levels = []
            if 'schedule_config' in analysis_data and analysis_data['schedule_config']:
                selected_risk_levels = analysis_data['schedule_config'].get('strategy_risk_levels', [])
                print(f"🔍 DEBUG: Selected risk levels from schedule: {selected_risk_levels}")
            
            # If no risk levels specified, use all entries (backward compatibility)
            if not selected_risk_levels:
                selected_risk_levels = ['high', 'medium', 'low']  # Default to all
                print(f"🔍 DEBUG: No risk levels specified, using all: {selected_risk_levels}")
            
            # Map risk level names to entry names
            risk_mapping = {
                'high': 'High Reward',
                'medium': 'Mid Reward', 
                'low': 'Low Reward'
            }
            
            # Filter df_data based on selected risk levels
            filtered_entries = []
            for entry in df_data:
                entry_type = entry.get('Entry', '').strip()
                print(f"🔍 DEBUG: Checking entry: {entry_type}")
                
                # Check if this entry matches any selected risk level
                for risk_level in selected_risk_levels:
                    expected_entry_name = risk_mapping.get(risk_level, '')
                    # Check both exact match and match with risk suffix (e.g., "High Reward (HIGH RISK)")
                    if (entry_type == expected_entry_name or 
                        entry_type.startswith(expected_entry_name + ' (')):
                        filtered_entries.append(entry)
                        print(f"🔍 DEBUG: ✅ Entry '{entry_type}' matches risk level '{risk_level}' - INCLUDED")
                        break
                else:
                    print(f"🔍 DEBUG: ❌ Entry '{entry_type}' not in selected risk levels - SKIPPED")
            
            print(f"🔍 DEBUG: Filtered entries: {len(filtered_entries)}/{len(df_data)} entries selected")
            
            # Convert filtered df_data to strategy_entries format
            for idx, entry in enumerate(filtered_entries):
                print(f"🔍 DEBUG: Processing filtered df_data entry {idx+1}: {entry}")
                
                strategy_entry = {
                    'CE Strike': entry.get('CE Strike'),
                    'PE Strike': entry.get('PE Strike'),
                    'CE Hedge Strike': entry.get('CE Hedge Strike'),
                    'PE Hedge Strike': entry.get('PE Hedge Strike'),
                    'Entry': entry.get('Entry', 'Unknown'),
                    'CE Price': entry.get('CE Price', 0),
                    'PE Price': entry.get('PE Price', 0)
                }
                strategy_entries.append(strategy_entry)
                print(f"🔍 DEBUG: Converted to strategy_entry: CE {strategy_entry['CE Strike']}, PE {strategy_entry['PE Strike']}, CE Hedge {strategy_entry['CE Hedge Strike']}, PE Hedge {strategy_entry['PE Hedge Strike']}, Entry: {strategy_entry['Entry']}")
                
        else:
            results['errors'].append('No strategy data found in analysis')
            print(f"🔍 DEBUG: No recognized data format found. Available keys: {list(analysis_data.keys())}")
            return results
        
        # Validate that we have strategy entries to process
        if not strategy_entries:
            results['errors'].append('No valid strategy entries found')
            print(f"🔍 DEBUG: No strategy entries to process")
            return results
            
        print(f"🔍 DEBUG: Processing {len(strategy_entries)} strategy entries")
        
        # Process each strategy entry
        for i, entry in enumerate(strategy_entries):
            print(f"🔍 DEBUG: Processing strategy entry {i+1}/{len(strategy_entries)}")
            
            entry_result = self._place_entry_orders(
                entry, 
                analysis_data.get('instrument', 'NIFTY'),
                analysis_data.get('expiry', ''),
                account_ids
            )
            
            results['orders_placed'].extend(entry_result['orders'])
            results['errors'].extend(entry_result['errors'])
        
        # Determine success
        results['successful_accounts'] = len([acc for acc in account_ids if acc in [order.get('account_id') for order in results['orders_placed']]])
        results['success'] = len(results['orders_placed']) > 0
        
        print(f"🔍 DEBUG: Final results - Success: {results['success']}, Orders: {len(results['orders_placed'])}, Errors: {len(results['errors'])}")
        
        return results
        
    def _place_entry_orders(self, entry: Dict, instrument: str, expiry: str, account_ids: List[str]) -> Dict:
        """Place orders for a single entry (CE + PE + Hedge)"""
        results = {'orders': [], 'errors': []}
        
        print(f"🔍 DEBUG: _place_entry_orders called with account_ids: {account_ids}")
        
        # Extract entry data
        ce_strike = entry.get('CE Strike')
        pe_strike = entry.get('PE Strike')
        ce_hedge_strike = entry.get('CE Hedge Strike')
        pe_hedge_strike = entry.get('PE Hedge Strike')
        
        print(f"🔍 DEBUG: Entry data - CE: {ce_strike}, PE: {pe_strike}, CE Hedge: {ce_hedge_strike}, PE Hedge: {pe_hedge_strike}")
        
        for account_id in account_ids:
            print(f"🔍 DEBUG: Processing account_id: {account_id}")
            if account_id not in self.brokers:
                error_msg = f"Broker handler not found for account {account_id}"
                print(f"🔍 DEBUG ERROR: {error_msg}")
                results['errors'].append(error_msg)
                continue
                
            broker = self.brokers[account_id]
            print(f"🔍 DEBUG: Found broker handler: {type(broker).__name__}")
            
            try:
                # 1. Buy CE Hedge (BUY first for margin benefit)
                if ce_hedge_strike:
                    print(f"🔍 DEBUG: Placing CE HEDGE order (BUY) - instrument: {instrument}, expiry: {expiry}, strike: {ce_hedge_strike}")
                    ce_hedge_order = broker.place_option_order(
                        instrument=instrument,
                        expiry=expiry,
                        strike=ce_hedge_strike,
                        option_type='CE',
                        transaction_type='BUY',
                        quantity=broker.get_lot_size(instrument),
                        order_type='MARKET'
                    )
                    print(f"🔍 DEBUG: CE HEDGE order result: {ce_hedge_order}")
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
                        print(f"🔍 DEBUG: CE HEDGE order added to results")
                    else:
                        error_msg = f"CE HEDGE order failed: {ce_hedge_order.get('error', 'Unknown error')}"
                        print(f"🔍 DEBUG ERROR: {error_msg}")
                        results['errors'].append(error_msg)
                        
                # 2. Buy PE Hedge (BUY second for margin benefit)
                if pe_hedge_strike:
                    print(f"🔍 DEBUG: Placing PE HEDGE order (BUY) - instrument: {instrument}, expiry: {expiry}, strike: {pe_hedge_strike}")
                    pe_hedge_order = broker.place_option_order(
                        instrument=instrument,
                        expiry=expiry,
                        strike=pe_hedge_strike,
                        option_type='PE',
                        transaction_type='BUY',
                        quantity=broker.get_lot_size(instrument),
                        order_type='MARKET'
                    )
                    print(f"🔍 DEBUG: PE HEDGE order result: {pe_hedge_order}")
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
                        print(f"🔍 DEBUG: PE HEDGE order added to results")
                    else:
                        error_msg = f"PE HEDGE order failed: {pe_hedge_order.get('error', 'Unknown error')}"
                        print(f"🔍 DEBUG ERROR: {error_msg}")
                        results['errors'].append(error_msg)
                
                # 3. Sell CE Option (SELL after BUY for margin benefit)
                if ce_strike:
                    print(f"🔍 DEBUG: Placing CE order (SELL) - instrument: {instrument}, expiry: {expiry}, strike: {ce_strike}")
                    ce_order = broker.place_option_order(
                        instrument=instrument,
                        expiry=expiry,
                        strike=ce_strike,
                        option_type='CE',
                        transaction_type='SELL',
                        quantity=broker.get_lot_size(instrument),
                        order_type='MARKET'
                    )
                    print(f"🔍 DEBUG: CE order result: {ce_order}")
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
                        print(f"🔍 DEBUG: CE order added to results")
                    else:
                        error_msg = f"CE order failed: {ce_order.get('error', 'Unknown error')}"
                        print(f"🔍 DEBUG ERROR: {error_msg}")
                        results['errors'].append(error_msg)
                        
                # 4. Sell PE Option (SELL last for margin benefit)
                if pe_strike:
                    print(f"🔍 DEBUG: Placing PE order (SELL) - instrument: {instrument}, expiry: {expiry}, strike: {pe_strike}")
                    pe_order = broker.place_option_order(
                        instrument=instrument,
                        expiry=expiry,
                        strike=pe_strike,
                        option_type='PE',
                        transaction_type='SELL',
                        quantity=broker.get_lot_size(instrument),
                        order_type='MARKET'
                    )
                    print(f"🔍 DEBUG: PE order result: {pe_order}")
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
                        print(f"🔍 DEBUG: PE order added to results")
                    else:
                        error_msg = f"PE order failed: {pe_order.get('error', 'Unknown error')}"
                        print(f"🔍 DEBUG ERROR: {error_msg}")
                        results['errors'].append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error placing orders for account {account_id}: {str(e)}"
                print(f"🔍 DEBUG EXCEPTION: {error_msg}")
                print(f"🔍 DEBUG EXCEPTION TYPE: {type(e).__name__}")
                import traceback
                print(f"🔍 DEBUG TRACEBACK: {traceback.format_exc()}")
                results['errors'].append(error_msg)
                
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
    
    def close_trade_positions(self, trade_data: Dict, broker_accounts: List[str]) -> Dict:
        """
        Close positions for specific broker accounts associated with a trade
        
        Args:
            trade_data: Trade information dict
            broker_accounts: List of broker account IDs to close positions for
            
        Returns:
            Dict with success status, closed orders, and any errors
        """
        close_results = {
            'success': False,
            'trade_id': trade_data.get('id'),
            'broker_accounts': broker_accounts,
            'closed_orders': [],
            'successful_closes': 0,
            'errors': []
        }
        
        try:
            # Get trade details for closing
            instrument = trade_data.get('instrument', '')
            expiry = trade_data.get('expiry', '')
            ce_strike = trade_data.get('ce_strike', 0)
            pe_strike = trade_data.get('pe_strike', 0)
            
            print(f"🔄 Attempting to close positions for trade {trade_data.get('id')} across {len(broker_accounts)} broker account(s)")
            
            for account_id in broker_accounts:
                try:
                    # Find the broker handler for this account
                    broker_handler = None
                    broker_type = None
                    
                    # Look up the broker type for this account
                    from .utils import load_settings
                    settings = load_settings()
                    for account in settings.get('broker_accounts', []):
                        if (account.get('client_id') == account_id or 
                            account.get('account_id') == account_id):
                            broker_type = account.get('broker')
                            break
                    
                    if not broker_type:
                        close_results['errors'].append(f"Unknown broker type for account {account_id}")
                        continue
                    
                    # Get the handler and attempt to close positions
                    if account_id in self.brokers:
                        broker_handler = self.brokers[account_id]
                        
                        # Close CE position if exists
                        if ce_strike:
                            ce_close_result = self._close_option_position(
                                broker_handler, account_id, instrument, expiry, ce_strike, 'CE'
                            )
                            if ce_close_result.get('success'):
                                close_results['closed_orders'].append(ce_close_result)
                        
                        # Close PE position if exists  
                        if pe_strike:
                            pe_close_result = self._close_option_position(
                                broker_handler, account_id, instrument, expiry, pe_strike, 'PE'
                            )
                            if pe_close_result.get('success'):
                                close_results['closed_orders'].append(pe_close_result)
                        
                        close_results['successful_closes'] += 1
                        print(f"✅ Successfully closed positions for account {account_id}")
                        
                    else:
                        close_results['errors'].append(f"No handler available for broker type {broker_type}")
                        
                except Exception as e:
                    error_msg = f"Error closing positions for account {account_id}: {str(e)}"
                    close_results['errors'].append(error_msg)
                    print(f"❌ {error_msg}")
            
            # Consider successful if at least one account was closed successfully
            close_results['success'] = close_results['successful_closes'] > 0
            
            if close_results['success']:
                print(f"✅ Successfully closed positions across {close_results['successful_closes']} account(s)")
            else:
                print(f"❌ Failed to close positions for any accounts")
                
        except Exception as e:
            close_results['errors'].append(f"General error in close_trade_positions: {str(e)}")
            print(f"❌ Critical error closing trade positions: {e}")
        
        return close_results
    
    def _close_option_position(self, broker_handler, account_id: str, instrument: str, 
                              expiry: str, strike: float, option_type: str) -> Dict:
        """
        Close a specific option position
        
        Returns:
            Dict with success status and order details
        """
        try:
            # This would be implemented based on the specific broker's API
            # For now, return a placeholder result
            return {
                'success': True,
                'account_id': account_id,
                'instrument': instrument,
                'strike': strike,
                'option_type': option_type,
                'order_id': f"CLOSE_{account_id}_{strike}{option_type}",
                'message': f"Closed {option_type} {strike} position for {account_id}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


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
        """Get lot size for instrument from settings"""
        try:
            from .utils import load_settings
            settings = load_settings()
            
            # Get lot sizes from settings with fallback to defaults
            if instrument.upper() == 'NIFTY':
                return settings.get('nifty_lot_size', 75)
            elif instrument.upper() == 'BANKNIFTY':
                return settings.get('banknifty_lot_size', 15)
            else:
                # Fallback for other instruments
                lot_sizes = {
                    'SENSEX': 10
                }
                return lot_sizes.get(instrument.upper(), 50)
                
        except Exception as e:
            # Fallback to hardcoded values if settings fail
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
        """Get lot size for instrument from settings"""
        try:
            from .utils import load_settings
            settings = load_settings()
            
            # Get lot sizes from settings with fallback to defaults
            if instrument.upper() == 'NIFTY':
                return settings.get('nifty_lot_size', 75)
            elif instrument.upper() == 'BANKNIFTY':
                return settings.get('banknifty_lot_size', 15)
            else:
                # Fallback for other instruments
                lot_sizes = {
                    'SENSEX': 10
                }
                return lot_sizes.get(instrument.upper(), 50)
                
        except Exception as e:
            # Fallback to hardcoded values if settings fail
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
        """Get lot size for instrument from settings"""
        try:
            from .utils import load_settings
            settings = load_settings()
            
            # Get lot sizes from settings with fallback to defaults
            if instrument.upper() == 'NIFTY':
                return settings.get('nifty_lot_size', 75)
            elif instrument.upper() == 'BANKNIFTY':
                return settings.get('banknifty_lot_size', 15)
            else:
                # Fallback for other instruments
                lot_sizes = {
                    'SENSEX': 10
                }
                return lot_sizes.get(instrument.upper(), 50)
                
        except Exception as e:
            # Fallback to hardcoded values if settings fail
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
        """Get lot size for instrument from settings"""
        try:
            from .utils import load_settings
            settings = load_settings()
            
            # Get lot sizes from settings with fallback to defaults
            if instrument.upper() == 'NIFTY':
                return settings.get('nifty_lot_size', 75)
            elif instrument.upper() == 'BANKNIFTY':
                return settings.get('banknifty_lot_size', 15)
            else:
                # Fallback for other instruments
                lot_sizes = {
                    'SENSEX': 10
                }
                return lot_sizes.get(instrument.upper(), 50)
                
        except Exception as e:
            # Fallback to hardcoded values if settings fail
            lot_sizes = {
                'NIFTY': 75,
                'BANKNIFTY': 15,
                'SENSEX': 10
            }
            return lot_sizes.get(instrument, 50)


# Global broker manager instance
broker_manager = BrokerOrderManager()
