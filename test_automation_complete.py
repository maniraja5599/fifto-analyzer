#!/usr/bin/env python3
"""
Test Complete Automation System
Tests both single and multiple automation functionality
"""

import os
import sys
import django
from datetime import datetime
import pytz

# Setup Django environment
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils

def test_automation_system():
    """Test the complete automation system."""
    
    print(f"🚀 Testing Complete Automation System")
    print(f"📅 Current Time: {datetime.now()}")
    
    # Get current IST time
    ist = pytz.timezone('Asia/Kolkata')
    current_time_ist = datetime.now(ist)
    print(f"🌍 Current IST Time: {current_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Test 1: Load current settings
    print("\n" + "="*50)
    print("📖 Test 1: Loading Current Settings")
    print("="*50)
    
    settings = utils.load_settings()
    print(f"✅ Settings loaded successfully")
    print(f"📊 Bot Token: {settings.get('bot_token', 'Not set')[:20]}...")
    print(f"📊 Chat ID: {settings.get('chat_id', 'Not set')}")
    print(f"📊 NIFTY Lot Size: {settings.get('nifty_lot_size', 75)}")
    print(f"📊 BANKNIFTY Lot Size: {settings.get('banknifty_lot_size', 35)}")
    
    # Test 2: Test automation readiness
    print("\n" + "="*50)
    print("🔧 Test 2: Testing Automation Readiness")
    print("="*50)
    
    try:
        # Test with bypass for current time
        test_config = {
            'name': 'Test Schedule',
            'enabled': True,
            'instruments': ['NIFTY', 'BANKNIFTY'],
            'nifty_calc_type': 'Weekly',
            'banknifty_calc_type': 'Monthly'
        }
        
        result = utils.test_specific_automation(test_config)
        print(f"✅ Automation test result: {result}")
        
    except Exception as e:
        print(f"❌ Automation test failed: {str(e)}")
    
    # Test 3: Market hours detection
    print("\n" + "="*50)
    print("⏰ Test 3: Market Hours Detection")
    print("="*50)
    
    current_hour = current_time_ist.hour
    current_minute = current_time_ist.minute
    current_weekday = current_time_ist.weekday()  # 0 = Monday, 6 = Sunday
    
    print(f"📅 Current Day: {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][current_weekday]}")
    print(f"⏰ Current Time: {current_hour:02d}:{current_minute:02d}")
    
    # Market hours: 9:15 AM to 3:30 PM IST, Monday to Friday
    is_market_day = current_weekday < 5  # Monday to Friday
    is_market_hours = (current_hour == 9 and current_minute >= 15) or (10 <= current_hour <= 14) or (current_hour == 15 and current_minute <= 30)
    
    print(f"📈 Is Market Day: {'✅ Yes' if is_market_day else '❌ No'}")
    print(f"📈 Is Market Hours: {'✅ Yes' if is_market_hours else '❌ No'}")
    print(f"📈 Market Status: {'🟢 OPEN' if (is_market_day and is_market_hours) else '🔴 CLOSED'}")
    
    # Test 4: Multiple automation structure
    print("\n" + "="*50)
    print("📋 Test 4: Multiple Automation Structure")
    print("="*50)
    
    multiple_automations = settings.get('multiple_automations', [])
    print(f"📊 Current Multiple Automations: {len(multiple_automations)}")
    
    if multiple_automations:
        for i, automation in enumerate(multiple_automations):
            print(f"  {i+1}. {automation.get('name', 'Unnamed')} - {'✅ Enabled' if automation.get('enabled') else '❌ Disabled'}")
            print(f"     Instruments: {', '.join(automation.get('instruments', []))}")
            print(f"     Days: {', '.join(automation.get('days', []))}")
            print(f"     Time: {automation.get('time', 'Not set')}")
    else:
        print("📝 No multiple automations configured yet")
    
    # Test 5: Telegram connectivity
    print("\n" + "="*50)
    print("📱 Test 5: Telegram Connectivity")
    print("="*50)
    
    try:
        bot_token = settings.get('bot_token')
        chat_id = settings.get('chat_id')
        
        if bot_token and chat_id:
            test_message = f"🧪 Automation System Test - {current_time_ist.strftime('%H:%M:%S')}"
            result = utils.send_telegram_message(test_message)
            print(f"📱 Telegram test: {'✅ Success' if result else '❌ Failed'}")
        else:
            print("📱 Telegram: ❌ Bot token or chat ID not configured")
    except Exception as e:
        print(f"📱 Telegram test error: {str(e)}")
    
    print("\n" + "="*60)
    print("🎯 AUTOMATION SYSTEM STATUS SUMMARY")
    print("="*60)
    print(f"⏰ System Time: {current_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"📈 Market Status: {'🟢 OPEN' if (is_market_day and is_market_hours) else '🔴 CLOSED'}")
    print(f"🔧 Settings: ✅ Loaded")
    print(f"📋 Multiple Schedules: {len(multiple_automations)} configured")
    print(f"📱 Telegram: {'✅ Configured' if (settings.get('bot_token') and settings.get('chat_id')) else '❌ Not configured'}")
    print("="*60)

if __name__ == "__main__":
    test_automation_system()
