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
        
        # Option Chain Refresh Settings - DISABLED for on-demand only
        self.option_chain_refresh_enabled = False
        self.option_chain_refresh_interval = 600  # 10 minutes default (rate limit optimization)
        self.option_chain_stop_event = Event()
        self.option_chain_thread = None
        self.last_option_chain_update = None
        
    def start_updater(self):
        """Start the 30-minute P&L update thread - DISABLED for on-demand only"""
        print("📝 Automatic P&L updates disabled - Use manual refresh when needed")
        # Automatic updater disabled - use manual refresh only
        # if self.update_thread is None or not self.update_thread.is_alive():
        #     self.stop_event.clear()
        #     self.update_thread = Thread(target=self._update_loop, daemon=True)
        #     self.update_thread.start()
        #     print("✅ P&L Updater started - 30 minute intervals")
            
        # Option chain refresh disabled - use on-demand only
        # self.start_option_chain_refresh()
            
    def stop_updater(self):
        """Stop the P&L update thread"""
        if self.update_thread and self.update_thread.is_alive():
            self.stop_event.set()
            self.update_thread.join(timeout=5)
            print("🛑 P&L Updater stopped")
            
        # Stop option chain refresh
        self.stop_option_chain_refresh()
            
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
            
    def start_option_chain_refresh(self):
        """Start option chain refresh thread"""
        if not self.option_chain_refresh_enabled:
            print("🔄 Option chain refresh is disabled")
            return
            
        if self.option_chain_thread is None or not self.option_chain_thread.is_alive():
            self.option_chain_stop_event.clear()
            self.option_chain_thread = Thread(target=self._option_chain_refresh_loop, daemon=True)
            self.option_chain_thread.start()
            interval_text = self._get_interval_text(self.option_chain_refresh_interval)
            print(f"✅ Option chain refresh started - {interval_text} intervals")
            
    def stop_option_chain_refresh(self):
        """Stop option chain refresh thread"""
        if self.option_chain_thread and self.option_chain_thread.is_alive():
            self.option_chain_stop_event.set()
            self.option_chain_thread.join(timeout=3)
            print("🛑 Option chain refresh stopped")
            
    def _option_chain_refresh_loop(self):
        """Option chain refresh loop"""
        while not self.option_chain_stop_event.is_set():
            try:
                if self._is_market_open():
                    self._refresh_option_chains()
                    self.last_option_chain_update = datetime.now()
                    interval_text = self._get_interval_text(self.option_chain_refresh_interval)
                    print(f"📊 Option chains refreshed at {self.last_option_chain_update.strftime('%H:%M:%S')} - Next refresh in {interval_text}")
                else:
                    print("🕐 Market closed - Option chain refresh skipped")
                    
            except Exception as e:
                print(f"❌ Option Chain Refresh Error: {e}")
                
            # Wait for the specified interval or until stop event
            self.option_chain_stop_event.wait(self.option_chain_refresh_interval)
            
    def _refresh_option_chains(self):
        """Refresh option chain data for active instruments"""
        try:
            # Get active trades to determine which instruments to refresh
            trades = utils.load_trades()
            active_trades = [t for t in trades if t.get('status') == 'Running']
            
            if not active_trades:
                print("📝 No active trades - skipping option chain refresh")
                return
                
            # Get unique instruments from active trades
            instruments = set(trade['instrument'] for trade in active_trades)
            
            for instrument in instruments:
                try:
                    print(f"🔄 Refreshing option chain for {instrument}...")
                    # Force refresh by calling DhanHQ API
                    option_data = self.dhan_api.get_option_chain(instrument)
                    if option_data:
                        print(f"✅ {instrument} option chain refreshed successfully")
                    else:
                        print(f"⚠️ Failed to refresh {instrument} option chain")
                        
                except Exception as e:
                    print(f"❌ Error refreshing {instrument} option chain: {e}")
                    
        except Exception as e:
            print(f"❌ Option chain refresh error: {e}")
            
    def set_option_chain_refresh_interval(self, interval_minutes):
        """Set option chain refresh interval
        
        Args:
            interval_minutes (int): Interval in minutes (1, 3, 5) or 0 to disable
        """
        if interval_minutes == 0:
            self.option_chain_refresh_enabled = False
            self.stop_option_chain_refresh()
            print("🛑 Option chain refresh disabled")
        else:
            self.option_chain_refresh_enabled = True
            self.option_chain_refresh_interval = interval_minutes * 60  # Convert to seconds
            
            # Restart the refresh thread with new interval
            if self.option_chain_thread and self.option_chain_thread.is_alive():
                self.stop_option_chain_refresh()
                
            self.start_option_chain_refresh()
            interval_text = self._get_interval_text(self.option_chain_refresh_interval)
            print(f"✅ Option chain refresh interval set to {interval_text}")
            
    def _get_interval_text(self, interval_seconds):
        """Convert interval seconds to readable text"""
        if interval_seconds < 60:
            return f"{interval_seconds} seconds"
        else:
            minutes = interval_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
            
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
                # Handle DhanHQ response structure: option_data['data']['oc'] contains the option chain
                oc_data = option_data['data'].get('oc', {})
                
                # Debugging: Check data types
                if not isinstance(oc_data, dict):
                    print(f"❌ Unexpected oc_data type: {type(oc_data)}, value: {str(oc_data)[:100]}...")
                    return None
                
                # Look for the specific strike in the oc dictionary
                strike_key = str(int(float(strike)))  # Convert to string key
                if strike_key in oc_data:
                    strike_data = oc_data[strike_key]
                    
                    if not isinstance(strike_data, dict):
                        print(f"❌ Unexpected strike_data type: {type(strike_data)}, value: {str(strike_data)[:100]}...")
                        return None
                    
                    # Get CE or PE data based on option_type
                    if option_type == 'CE' and 'ce' in strike_data:
                        ce_data = strike_data['ce']
                        if isinstance(ce_data, dict):
                            return ce_data.get('last_price', 0)
                        else:
                            print(f"❌ CE data is not dict: {type(ce_data)}")
                    elif option_type == 'PE' and 'pe' in strike_data:
                        pe_data = strike_data['pe']
                        if isinstance(pe_data, dict):
                            return pe_data.get('last_price', 0)
                        else:
                            print(f"❌ PE data is not dict: {type(pe_data)}")
                        
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
        """Get current status of P&L updater and option chain refresh"""
        return {
            'is_running': self.update_thread and self.update_thread.is_alive(),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'next_update': (self.last_update + timedelta(seconds=self.update_interval)).isoformat() if self.last_update else None,
            'market_open': self._is_market_open(),
            'update_interval': f"{self.update_interval // 60} minutes",
            'option_chain_refresh': {
                'enabled': self.option_chain_refresh_enabled,
                'is_running': self.option_chain_thread and self.option_chain_thread.is_alive(),
                'interval': f"{self.option_chain_refresh_interval // 60} minute{'s' if self.option_chain_refresh_interval // 60 != 1 else ''}",
                'last_refresh': self.last_option_chain_update.isoformat() if self.last_option_chain_update else None,
                'next_refresh': (self.last_option_chain_update + timedelta(seconds=self.option_chain_refresh_interval)).isoformat() if self.last_option_chain_update else None
            }
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
