"""
Position Monitoring Service
==========================

Monitors live trading positions and automatically closes them when:
- Target profit is reached
- Stop loss is hit
- Market conditions warrant closure

Features:
- Real-time P&L monitoring
- Multi-broker position tracking
- Automatic order placement for exits
- Telegram notifications for exits
- Risk management safeguards
"""

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class PositionMonitoringService:
    """Service to monitor live trading positions across multiple brokers"""
    
    def __init__(self):
        self.running = False
        self.monitor_thread = None
        self.monitoring_interval = 30  # Check every 30 seconds
        self.active_positions = {}
        self.closed_positions = []
        
    def start_monitoring(self):
        """Start the position monitoring service"""
        if self.running:
            logger.info("Position monitoring is already running")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Position monitoring service started")
        
    def stop_monitoring(self):
        """Stop the position monitoring service"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Position monitoring service stopped")
        
    def add_position_for_monitoring(self, trade_data: Dict, broker_orders: List[Dict]):
        """
        Add a new position for monitoring
        
        Args:
            trade_data: Trade information with target/stoploss
            broker_orders: List of broker orders that were placed
        """
        trade_id = trade_data.get('id')
        if not trade_id:
            return
            
        position_info = {
            'trade_id': trade_id,
            'instrument': trade_data.get('instrument'),
            'expiry': trade_data.get('expiry'),
            'target_amount': trade_data.get('target_amount'),
            'stoploss_amount': trade_data.get('stoploss_amount'),
            'entry_time': datetime.now(),
            'broker_orders': broker_orders,
            'status': 'ACTIVE',
            'last_pnl': 0.0,
            'peak_pnl': 0.0,
            'drawdown': 0.0
        }
        
        self.active_positions[trade_id] = position_info
        logger.info(f"Added position {trade_id} for monitoring")
        
    def remove_position_from_monitoring(self, trade_id: str):
        """Remove a position from monitoring"""
        if trade_id in self.active_positions:
            position = self.active_positions.pop(trade_id)
            position['status'] = 'REMOVED'
            position['exit_time'] = datetime.now()
            self.closed_positions.append(position)
            logger.info(f"Removed position {trade_id} from monitoring")
            
    def _monitoring_loop(self):
        """Main monitoring loop that runs continuously"""
        logger.info("Position monitoring loop started")
        
        while self.running:
            try:
                if self.active_positions:
                    self._check_all_positions()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
                
        logger.info("Position monitoring loop stopped")
        
    def _check_all_positions(self):
        """Check all active positions for exit conditions"""
        positions_to_close = []
        
        for trade_id, position in self.active_positions.items():
            try:
                current_pnl = self._calculate_position_pnl(position)
                position['last_pnl'] = current_pnl
                
                # Update peak P&L and drawdown
                if current_pnl > position['peak_pnl']:
                    position['peak_pnl'] = current_pnl
                    
                position['drawdown'] = position['peak_pnl'] - current_pnl
                
                # Check exit conditions
                exit_reason = self._check_exit_conditions(position, current_pnl)
                if exit_reason:
                    positions_to_close.append((trade_id, exit_reason))
                    
            except Exception as e:
                logger.error(f"Error checking position {trade_id}: {e}")
                
        # Close positions that meet exit criteria
        for trade_id, reason in positions_to_close:
            self._close_position(trade_id, reason)
            
    def _calculate_position_pnl(self, position: Dict) -> float:
        """Calculate current P&L for a position"""
        try:
            # This would integrate with the broker APIs to get live P&L
            # For now, we'll use the existing trade P&L calculation method
            from . import utils
            
            trade_id = position['trade_id']
            trades = utils.load_trades()
            trade = next((t for t in trades if t['id'] == trade_id), None)
            
            if trade:
                # Get current market data
                instrument = trade['instrument']
                chain_data = utils.get_option_chain_data(instrument)
                
                if chain_data:
                    current_ce, current_pe = 0.0, 0.0
                    
                    # Handle NSE data structure
                    records = chain_data.get('records', {})
                    if records and 'data' in records and isinstance(records['data'], list):
                        for item in records['data']:
                            if item.get("expiryDate") == trade.get('expiry'):
                                if item.get("strikePrice") == trade.get('ce_strike') and item.get("CE"):
                                    current_ce = item["CE"]["lastPrice"]
                                if item.get("strikePrice") == trade.get('pe_strike') and item.get("PE"):
                                    current_pe = item["PE"]["lastPrice"]
                    
                    # Calculate P&L
                    lot_size = utils.get_lot_size(trade['instrument'])
                    initial_premium = trade.get('initial_premium', 0)
                    current_premium = current_ce + current_pe
                    
                    if current_premium > 0:
                        return round((initial_premium - current_premium) * lot_size, 2)
                        
        except Exception as e:
            logger.error(f"Error calculating P&L for position {position['trade_id']}: {e}")
            
        return 0.0
        
    def _check_exit_conditions(self, position: Dict, current_pnl: float) -> Optional[str]:
        """Check if position should be closed based on current P&L"""
        target_amount = position.get('target_amount')
        stoploss_amount = position.get('stoploss_amount')
        
        # Check target hit
        if target_amount and current_pnl >= target_amount:
            return 'TARGET_HIT'
            
        # Check stoploss hit
        if stoploss_amount and current_pnl <= -stoploss_amount:
            return 'STOPLOSS_HIT'
            
        # Check time-based exit (e.g., close 30 minutes before market close)
        current_time = datetime.now().time()
        market_close_time = datetime.strptime("15:00", "%H:%M").time()
        
        if current_time >= datetime.strptime("14:30", "%H:%M").time():
            return 'TIME_EXIT'
            
        # Check for excessive drawdown (risk management)
        max_drawdown_percent = 50  # 50% of peak profit
        if position['peak_pnl'] > 0 and position['drawdown'] > (position['peak_pnl'] * max_drawdown_percent / 100):
            return 'DRAWDOWN_EXIT'
            
        return None
        
    def _close_position(self, trade_id: str, reason: str):
        """Close a position by placing exit orders"""
        try:
            position = self.active_positions.get(trade_id)
            if not position:
                return
                
            logger.info(f"Closing position {trade_id} due to {reason}")
            
            # Load broker manager and place exit orders
            from .broker_manager import broker_manager
            
            # Get the original orders for this position
            broker_orders = position.get('broker_orders', [])
            
            # Place reverse orders to close positions
            exit_orders = []
            for order in broker_orders:
                account_id = order['account_id']
                
                if account_id in broker_manager.brokers:
                    broker = broker_manager.brokers[account_id]
                    
                    # Reverse the transaction type
                    exit_transaction = 'BUY' if order['transaction'] == 'SELL' else 'SELL'
                    
                    exit_order = broker.place_option_order(
                        instrument=order['instrument'],
                        expiry=position['expiry'],
                        strike=order['strike'],
                        option_type=order['option_type'],
                        transaction_type=exit_transaction,
                        quantity=broker.get_lot_size(order['instrument']),
                        order_type='MARKET'
                    )
                    
                    if exit_order['success']:
                        exit_orders.append({
                            'account_id': account_id,
                            'order_id': exit_order['order_id'],
                            'original_order': order,
                            'exit_reason': reason
                        })
                        
            # Update position status
            position['status'] = 'CLOSED'
            position['exit_time'] = datetime.now()
            position['exit_reason'] = reason
            position['exit_orders'] = exit_orders
            position['final_pnl'] = position['last_pnl']
            
            # Move to closed positions
            self.closed_positions.append(position)
            del self.active_positions[trade_id]
            
            # Update trade status in the system
            self._update_trade_status(trade_id, reason, position['final_pnl'])
            
            # Send notification
            self._send_close_notification(position, reason)
            
            logger.info(f"Position {trade_id} closed successfully with {len(exit_orders)} exit orders")
            
        except Exception as e:
            logger.error(f"Error closing position {trade_id}: {e}")
            
    def _update_trade_status(self, trade_id: str, reason: str, final_pnl: float):
        """Update trade status in the main trades database"""
        try:
            from . import utils
            
            trades = utils.load_trades()
            for trade in trades:
                if trade['id'] == trade_id:
                    trade['status'] = 'Closed'
                    trade['close_reason'] = reason
                    trade['final_pnl'] = final_pnl
                    trade['close_time'] = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
                    break
                    
            utils.save_trades(trades)
            
        except Exception as e:
            logger.error(f"Error updating trade status for {trade_id}: {e}")
            
    def _send_close_notification(self, position: Dict, reason: str):
        """Send Telegram notification about position closure"""
        try:
            from . import utils
            
            trade_id = position['trade_id']
            instrument = position['instrument']
            final_pnl = position['final_pnl']
            
            message = f"🔔 **Position Closed**\n\n"
            message += f"📊 Trade: {trade_id}\n"
            message += f"📈 Instrument: {instrument}\n"
            message += f"💰 Final P&L: ₹{final_pnl:,.2f}\n"
            message += f"🎯 Reason: {reason.replace('_', ' ').title()}\n"
            message += f"⏰ Time: {datetime.now().strftime('%I:%M:%S %p')}"
            
            utils.send_telegram_message(message)
            
        except Exception as e:
            logger.error(f"Error sending close notification: {e}")
            
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status"""
        return {
            'running': self.running,
            'active_positions': len(self.active_positions),
            'total_closed': len(self.closed_positions),
            'positions': list(self.active_positions.keys()),
            'last_check': datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        }


# Global position monitoring service instance
position_monitor = PositionMonitoringService()
