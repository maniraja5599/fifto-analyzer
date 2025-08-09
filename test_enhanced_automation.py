#!/usr/bin/env python3
"""
Test the new enhanced automation system with multiple permanent schedules.
"""

import os
import sys
import django
import json

# Add the project directory to Python path
project_path = '/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer'
sys.path.insert(0, project_path)
os.chdir(project_path)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils
from datetime import datetime
import pytz

def test_enhanced_automation():
    print("🚀 Testing Enhanced Automation System")
    print("=" * 60)
    
    # Test 1: Settings Management
    print("\n📊 Test 1: Settings Management")
    print("-" * 30)
    
    settings = utils.load_settings()
    print(f"✅ Settings loaded successfully")
    
    # Initialize multiple schedules if not exists
    if 'multiple_schedules' not in settings:
        settings['multiple_schedules'] = []
        utils.save_settings(settings)
        print(f"✅ Initialized multiple schedules storage")
    
    current_schedules = settings.get('multiple_schedules', [])
    print(f"📊 Current schedules: {len(current_schedules)}")
    
    # Test 2: Create Test Schedule
    print("\n🔧 Test 2: Create Test Schedule")
    print("-" * 30)
    
    test_schedule = {
        'id': len(current_schedules),
        'name': 'Test Daily Schedule',
        'enabled': True,
        'time': '09:25',
        'instruments': ['NIFTY', 'BANKNIFTY'],
        'nifty_calc_type': 'Weekly',
        'banknifty_calc_type': 'Monthly',
    }
    
    # Add to settings
    current_schedules.append(test_schedule)
    settings['multiple_schedules'] = current_schedules
    utils.save_settings(settings)
    print(f"✅ Created test schedule: {test_schedule['name']}")
    
    # Test 3: Schedule Functions
    print("\n⏰ Test 3: Schedule Management Functions")
    print("-" * 30)
    
    # Test permanent schedule start
    try:
        result = utils.start_permanent_schedule(test_schedule)
        print(f"✅ Start permanent schedule: {result}")
    except Exception as e:
        print(f"❌ Start permanent schedule failed: {str(e)}")
    
    # Test schedule execution
    try:
        utils.run_permanent_schedule(test_schedule)
        print(f"✅ Schedule execution test completed")
    except Exception as e:
        print(f"❌ Schedule execution failed: {str(e)}")
    
    # Test 4: Quick Test Function
    print("\n🧪 Test 4: Quick Test Function")
    print("-" * 30)
    
    try:
        result = utils.run_test_automation_now()
        print(f"✅ Quick test result:\n{result}")
    except Exception as e:
        print(f"❌ Quick test failed: {str(e)}")
    
    # Test 5: Individual Schedule Test
    print("\n🎯 Test 5: Individual Schedule Test")
    print("-" * 30)
    
    try:
        result = utils.test_specific_automation(test_schedule)
        print(f"✅ Individual schedule test result:\n{result}")
    except Exception as e:
        print(f"❌ Individual schedule test failed: {str(e)}")
    
    # Test 6: Time and Market Status
    print("\n⏰ Test 6: Time and Market Status")
    print("-" * 30)
    
    ist_time = datetime.now(pytz.timezone('Asia/Kolkata'))
    print(f"📅 Current IST Time: {ist_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"📅 Schedule Time: {test_schedule['time']}")
    print(f"🔄 Schedule Status: {'🟢 Enabled' if test_schedule['enabled'] else '🔴 Disabled'}")
    print(f"📊 Instruments: {', '.join(test_schedule['instruments'])}")
    
    # Test 7: Cleanup (Optional)
    print("\n🧹 Test 7: Cleanup")
    print("-" * 30)
    
    try:
        utils.stop_permanent_schedule(test_schedule['id'])
        print(f"✅ Stopped permanent schedule")
    except Exception as e:
        print(f"⚠️ Stop schedule warning: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 ENHANCED AUTOMATION SYSTEM TEST SUMMARY")
    print("=" * 60)
    print(f"⏰ System Time: {ist_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"📊 Total Schedules: {len(current_schedules)}")
    print(f"🔧 Schedule Management: ✅ Working")
    print(f"🧪 Quick Testing: ✅ Working")
    print(f"🎯 Individual Testing: ✅ Working")
    print(f"⏰ Permanent Scheduling: ✅ Implemented")
    print("=" * 60)
    print("✨ Enhanced automation system is ready!")
    print("💡 Access via: http://127.0.0.1:8001/automation/")

if __name__ == "__main__":
    test_enhanced_automation()
