#!/usr/bin/env python3
"""
Test automation functionality and provide debugging information
"""
import os
import sys
import django
import pytz

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')
django.setup()

from analyzer.utils import run_automated_chart_generation, load_settings
from datetime import datetime
from django.utils import timezone

def test_automation_debug():
    """Test automation with detailed debugging info"""
    print("🔍 AUTOMATION DEBUG TEST - TIMEZONE FIXED")
    print("=" * 60)
    
    # Timezone information
    print("\n🌍 TIMEZONE INFORMATION:")
    ist_tz = pytz.timezone('Asia/Kolkata')
    utc_time = datetime.utcnow()
    ist_time = timezone.now().astimezone(ist_tz)
    
    print(f"🌐 UTC Time: {utc_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🇮🇳 IST Time: {ist_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 Django Timezone: {timezone.get_current_timezone()}")
    
    # Load current settings
    print("\n📋 Loading Settings...")
    settings = load_settings()
    
    print(f"✅ Auto Generation Enabled: {settings.get('enable_auto_generation', False)}")
    print(f"📅 Scheduled Days: {settings.get('auto_gen_days', [])}")
    print(f"⏰ Scheduled Time: {settings.get('auto_gen_time', 'Not set')}")
    print(f"📈 Instruments: {settings.get('auto_gen_instruments', [])}")
    print(f"📊 NIFTY Calc Type: {settings.get('nifty_calc_type', 'Not set')}")
    print(f"📊 BANKNIFTY Calc Type: {settings.get('banknifty_calc_type', 'Not set')}")
    
    # Current time info (IST)
    print(f"\n🕐 Current IST Time: {ist_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📆 Current Day: {ist_time.strftime('%A')}")
    
    # Market hours check
    market_open = ist_time.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = ist_time.replace(hour=15, minute=30, second=0, microsecond=0)
    is_weekday = ist_time.weekday() < 5
    is_market_hours = market_open <= ist_time <= market_close
    
    print(f"🏢 Market Status: {'Open' if is_weekday and is_market_hours else 'Closed'}")
    print(f"📊 Market Hours: 9:15 AM - 3:30 PM IST")
    print(f"📅 Market Days: Monday - Friday")
    
    # Schedule analysis
    if settings.get('auto_gen_time'):
        scheduled_time = settings.get('auto_gen_time')
        print(f"\n⏰ SCHEDULE ANALYSIS:")
        print(f"🕐 Scheduled Time: {scheduled_time}")
        
        schedule_hour, schedule_minute = map(int, scheduled_time.split(':'))
        scheduled_today = ist_time.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
        time_diff = (ist_time - scheduled_today).total_seconds() / 60
        
        print(f"🔍 Time difference: {time_diff:.1f} minutes")
        
        if time_diff < -15:
            print("⏳ Status: Too early (more than 15 min before)")
        elif time_diff > 60:
            print("⌛ Status: Too late (more than 1 hour after)")
        else:
            print("✅ Status: Within execution window")
    
    # Test the automation function
    print("\n🚀 Testing Automation Function...")
    try:
        result = run_automated_chart_generation()
        print(f"📤 Result: {result}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Debug test completed!")

if __name__ == "__main__":
    test_automation_debug()
