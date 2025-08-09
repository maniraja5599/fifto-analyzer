#!/usr/bin/env python3
"""
Clear all automation schedules from the database/settings
This script will remove all existing automation schedules that might have invalid IDs
"""

import os
import sys
import json
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

import django
django.setup()

from analyzer import utils

def clear_automation_schedules():
    """Clear all automation schedules from settings"""
    try:
        print("🧹 Starting automation schedule cleanup...")
        
        # Load current settings
        settings = utils.load_settings()
        
        # Check current schedules
        multiple_schedules = settings.get('multiple_schedules', [])
        if not multiple_schedules:
            print("✅ No automation schedules found. Nothing to clear.")
            return
        
        print(f"📋 Found {len(multiple_schedules)} automation schedules:")
        for i, schedule in enumerate(multiple_schedules, 1):
            print(f"   {i}. {schedule.get('name', 'Unknown')} (ID: {schedule.get('id', 'Unknown')})")
        
        # Stop all running schedules (if any)
        print("\n⏹️  Stopping all running schedules...")
        for schedule in multiple_schedules:
            schedule_id = schedule.get('id')
            if schedule_id:
                try:
                    utils.stop_permanent_schedule(schedule_id)
                    print(f"   Stopped schedule: {schedule.get('name', 'Unknown')}")
                except Exception as e:
                    print(f"   Warning: Could not stop schedule {schedule.get('name', 'Unknown')}: {e}")
        
        # Clear all schedules
        print("\n🗑️  Clearing all automation schedules...")
        settings['multiple_schedules'] = []
        
        # Save the updated settings
        utils.save_settings(settings)
        
        print("✅ All automation schedules have been cleared successfully!")
        print("📝 You can now create new schedules from the automation page.")
        
        # Also clear any automation activities related to schedules
        if 'automation_activities' in settings:
            print("\n🧹 Clearing automation activities...")
            settings['automation_activities'] = []
            utils.save_settings(settings)
            print("✅ Automation activities cleared.")
        
    except Exception as e:
        print(f"❌ Error clearing automation schedules: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AUTOMATION SCHEDULE CLEANUP TOOL")
    print("=" * 60)
    print("This will remove ALL existing automation schedules.")
    print("You will need to recreate them after this cleanup.")
    print("=" * 60)
    
    # Ask for confirmation
    response = input("\nDo you want to proceed? (yes/no): ").lower().strip()
    
    if response in ['yes', 'y']:
        if clear_automation_schedules():
            print("\n🎉 Cleanup completed successfully!")
            print("   You can now go to the automation page and create new schedules.")
        else:
            print("\n❌ Cleanup failed. Please check the error messages above.")
    else:
        print("\n❌ Cleanup cancelled.")
    
    print("\n" + "=" * 60)
