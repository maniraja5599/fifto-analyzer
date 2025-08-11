"""
P&L Updater Module for Active Trades - Auto updates every 30 minutes
"""
import json
import os
import time
from datetime import datetime, timedelta
from threading import Thread, Event
import requests
from . import utils
from .dhan_api import DhanHQIntegration  # unified import replacing duplicate
from django.conf import settings

class PnLUpdater:
    def __init__(self):
        self.stop_event = Event()
        self.update_thread = None
        self.dhan_api = DhanHQIntegration()
        self.last_update = None
        self.update_interval = 30 * 60  # 30 minutes in seconds
        
    def start_updater(self):
        """Start the 30-minute P&L update thread"""
        if self.update_thread is None or not self.update_thread.is_alive():
            self.stop_event.clear()
            self.update_thread = Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            print("✅ P&L Updater started - 30 minute intervals")
            
    def stop_updater(self):
        """Stop the P&L update thread"""
        if self.update_thread and self.update_thread.is_alive():
            self.stop_event.set()
            self.update_thread.join(timeout=5)
            print("🛑 P&L Updater stopped")
            
    def _update_loop(self):
        """Main update loop - runs every 30 minutes"""
        while not self.stop_event.is_set():
            try:
                # Check if market is open (9:15 AM to 3:30 PM IST)
                if self._is_market_open():
                    self._update_active_trades_pnl()
                    self.last_update = datetime.now()
                    print(f"📊 Active trades P&L updated at {self.last_update.strftime('%H:%M:%S')}")
                else:
                    print("🕐 Market closed - P&L update skipped")
                    
            except Exception as e:
                print(f"❌ P&L Update Error: {e}")
                
            # Wait for 30 minutes or until stop event
            self.stop_event.wait(self.update_interval)
            
    def _is_market_open(self):
        """Check if market is currently open"""
        now = datetime.now()
        # Market hours: 9:15 AM to 3:30 PM IST
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Check if today is weekday and within market hours
        is_weekday = now.weekday() < 5  # Monday=0, Friday=4
        is_market_time = market_open <= now <= market_close
        
        return is_weekday and is_market_time
        
    def _update_active_trades_pnl(self):
        """Update P&L for all active trades using live option prices"""
        try:
            trades = utils.load_trades()
            active_trades = [t for t in trades if t.get('status') == 'Running']
            
            if not active_trades:
                print("📝 No active trades to update")
                return
                
            updated_count = 0
            
            for trade in active_trades:
                try:
                    # Get current option prices for the trade
                    current_ce_price = self._get_option_price(
                        trade['instrument'], 
                        trade['ce_strike'], 
                        trade['expiry'], 
                        'CE'
                    )
                    
                    current_pe_price = self._get_option_price(
                        trade['instrument'], 
                        trade['pe_strike'], 
                        trade['expiry'], 
                        'PE'
                    )
                    
                    if current_ce_price and current_pe_price:
                        # Calculate new P&L
                        lot_size = utils.get_lot_size(trade['instrument'])
                        new_pnl = (trade['initial_premium'] - (current_ce_price + current_pe_price)) * lot_size
                        
                        # Update trade with new P&L
                        old_pnl = trade.get('pnl', 0)
                        trade['pnl'] = new_pnl
                        trade['last_pnl_update'] = datetime.now().isoformat()
                        
                        # Check for target/stoploss
                        if new_pnl >= trade['target_amount']:
                            trade['status'] = 'Auto Closed - Target Hit'
                            trade['final_pnl'] = new_pnl
                            trade['closed_date'] = datetime.now().isoformat()
                            print(f"🎯 Target hit: {trade['id']} - P&L: ₹{new_pnl:,.2f}")
                            
                        elif new_pnl <= -trade['stoploss_amount']:
                            trade['status'] = 'Auto Closed - Stoploss Hit'
                            trade['final_pnl'] = new_pnl
                            trade['closed_date'] = datetime.now().isoformat()
                            print(f"🛑 Stoploss hit: {trade['id']} - P&L: ₹{new_pnl:,.2f}")
                            
                        updated_count += 1
                        print(f"📈 Updated {trade['id']}: ₹{old_pnl:,.2f} → ₹{new_pnl:,.2f}")
                        
                except Exception as e:
                    print(f"❌ Error updating trade {trade.get('id', 'unknown')}: {e}")
                    continue
                    
            # Save updated trades
            if updated_count > 0:
                utils.save_trades(trades)
                print(f"✅ Updated {updated_count} active trades")
            else:
                print("⚠️ No trades updated - check option data")
                
        except Exception as e:
            print(f"❌ P&L Update Error: {e}")
            
    def _get_option_price(self, instrument, strike, expiry, option_type):
        """Get current option price from DhanHQ"""
        try:
            # Use DhanHQ option chain data
            option_data = self.dhan_api.get_option_chain(instrument)
            
            if option_data and 'data' in option_data:
                for item in option_data['data']:
                    if (item.get('strike_price') == float(strike) and 
                        item.get('expiry_date') == expiry and
                        item.get('option_type') == option_type):
                        return item.get('ltp', 0)
                        
            # Fallback to NSE if DhanHQ fails
            return self._get_nse_option_price(instrument, strike, expiry, option_type)
            
        except Exception as e:
            print(f"❌ Option price fetch error: {e}")
            return None
            
    def _get_nse_option_price(self, instrument, strike, expiry, option_type):
        """Fallback to NSE option chain"""
        try:
            # Use the existing NSE option chain function
            chain = utils.get_option_chain_data(instrument)
            
            if chain and 'records' in chain and 'data' in chain['records']:
                for item in chain['records']['data']:
                    if (item.get('strikePrice') == float(strike) and
                        item.get('expiryDate') == expiry):
                        if option_type == 'CE' and 'CE' in item:
                            return item['CE'].get('lastPrice', 0)
                        elif option_type == 'PE' and 'PE' in item:
                            return item['PE'].get('lastPrice', 0)
                            
            return 0
            
        except Exception as e:
            print(f"❌ NSE fallback error: {e}")
            return 0
            
    def get_status(self):
        """Get current status of P&L updater"""
        return {
            'is_running': self.update_thread and self.update_thread.is_alive(),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'next_update': (self.last_update + timedelta(seconds=self.update_interval)).isoformat() if self.last_update else None,
            'market_open': self._is_market_open(),
            'update_interval': f"{self.update_interval // 60} minutes"
        }
        
    def force_update(self):
        """Force immediate P&L update (for settings refresh)"""
        try:
            print("🔄 Force updating active trades P&L...")
            self._update_active_trades_pnl()
            self.last_update = datetime.now()
            return True
        except Exception as e:
            print(f"❌ Force update error: {e}")
            return False

# Global instance
pnl_updater = PnLUpdater()
