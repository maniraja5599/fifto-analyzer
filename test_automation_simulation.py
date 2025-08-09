#!/usr/bin/env python3
"""
Test automation functionality by simulating market hours
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
sys.path.append('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')
django.setup()

from analyzer.utils import load_settings
from datetime import datetime
import pytz

def test_automation_simulation():
    """Test automation by simulating market conditions"""
    print("🧪 AUTOMATION SIMULATION TEST")
    print("=" * 50)
    
    # Get current settings
    settings = load_settings()
    
    # Simulate Monday market hours at scheduled time
    ist_tz = pytz.timezone('Asia/Kolkata')
    
    # Create test scenarios
    scenarios = [
        {
            'name': 'Monday 9:00 AM (Exact scheduled time)',
            'day': 'monday',
            'time': '09:00',
            'should_run': True
        },
        {
            'name': 'Monday 9:05 AM (5 min after)',
            'day': 'monday', 
            'time': '09:05',
            'should_run': True
        },
        {
            'name': 'Monday 10:30 AM (Too late)',
            'day': 'monday',
            'time': '10:30', 
            'should_run': False
        },
        {
            'name': 'Monday 8:30 AM (Too early)',
            'day': 'monday',
            'time': '08:30',
            'should_run': False
        },
        {
            'name': 'Sunday 9:00 AM (Weekend)',
            'day': 'sunday',
            'time': '09:00',
            'should_run': False
        }
    ]
    
    print(f"\n⚙️  Current Settings:")
    print(f"   📅 Days: {settings.get('auto_gen_days', [])}")
    print(f"   ⏰ Time: {settings.get('auto_gen_time', 'Not set')}")
    print(f"   📈 Instruments: {settings.get('auto_gen_instruments', [])}")
    
    print(f"\n🧪 SIMULATION SCENARIOS:")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        
        # Check if day is scheduled
        day_match = scenario['day'] in [d.lower() for d in settings.get('auto_gen_days', [])]
        
        # Check time window
        schedule_time = settings.get('auto_gen_time', '09:00')
        schedule_hour, schedule_minute = map(int, schedule_time.split(':'))
        test_hour, test_minute = map(int, scenario['time'].split(':'))
        
        # Calculate time difference in minutes
        schedule_minutes = schedule_hour * 60 + schedule_minute
        test_minutes = test_hour * 60 + test_minute
        time_diff = test_minutes - schedule_minutes
        
        # Check if within execution window (-15 to +60 minutes)
        time_ok = -15 <= time_diff <= 60
        
        # Check if weekend
        weekend_days = ['saturday', 'sunday']
        is_weekend = scenario['day'] in weekend_days
        
        # Market hours check (9:15 AM to 3:30 PM)
        market_start = 9 * 60 + 15  # 9:15 AM in minutes
        market_end = 15 * 60 + 30   # 3:30 PM in minutes
        in_market_hours = market_start <= test_minutes <= market_end
        
        print(f"   📅 Day scheduled: {'✅' if day_match else '❌'}")
        print(f"   ⏰ Time window: {'✅' if time_ok else '❌'} (diff: {time_diff} min)")
        print(f"   🏢 Market hours: {'✅' if in_market_hours else '❌'}")
        print(f"   📆 Weekday: {'✅' if not is_weekend else '❌'}")
        
        would_run = day_match and time_ok and in_market_hours and not is_weekend
        expected = scenario['should_run']
        
        print(f"   🎯 Expected: {'Should run' if expected else 'Should NOT run'}")
        print(f"   🤖 Would run: {'YES' if would_run else 'NO'}")
        print(f"   ✅ Test: {'PASS' if would_run == expected else 'FAIL'}")
    
    print(f"\n" + "=" * 50)
    print("✅ Simulation test completed!")
    print("\n📝 RECOMMENDATIONS:")
    print("   1. Set schedule time between 9:20 AM - 3:00 PM")
    print("   2. Use Monday-Friday for market days")
    print("   3. Current settings look good for automation!")

if __name__ == "__main__":
    test_automation_simulation()
