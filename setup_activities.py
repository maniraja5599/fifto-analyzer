#!/usr/bin/env python3
"""
Add test automation activities and setup popup notifications
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
from datetime import datetime

def add_test_activities():
    """Add some test automation activities"""
    print("🧪 Adding test automation activities...")
    
    # Add some sample activities
    test_activities = [
        ("Schedule Created", "Created new schedule: NIFTY Weekly Analysis", "success"),
        ("Charts Generated", "NIFTY charts generated successfully at 09:20 AM", "success"),
        ("Portfolio Updated", "Charts automatically added to active portfolio", "success"),
        ("BANKNIFTY Analysis", "BANKNIFTY monthly analysis completed", "success"),
        ("Telegram Alert", "Alert sent: New trades available for review", "success"),
        ("Schedule Updated", "Modified NIFTY schedule timing to 09:30 AM", "success"),
        ("Auto Generation", "Automated chart generation completed for 2 instruments", "success"),
    ]
    
    for title, description, status in test_activities:
        utils.add_automation_activity(title, description, status)
        print(f"   ✅ Added: {title}")
    
    print(f"📋 {len(test_activities)} test activities added successfully!")

def check_current_activities():
    """Check what activities currently exist"""
    print("\n📋 Current automation activities:")
    activities = utils.get_recent_automation_activities(limit=20)
    
    if activities:
        for i, activity in enumerate(activities, 1):
            print(f"   {i}. {activity['title']} - {activity['time']}")
    else:
        print("   No activities found")
    
    return len(activities)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AUTOMATION ACTIVITIES SETUP")
    print("=" * 60)
    
    # Check existing activities
    count = check_current_activities()
    
    if count == 0:
        print("\n🔄 No activities found. Adding test activities...")
        add_test_activities()
    else:
        print(f"\n✅ Found {count} existing activities.")
        response = input("Do you want to add more test activities? (yes/no): ").lower().strip()
        if response in ['yes', 'y']:
            add_test_activities()
    
    print("\n" + "=" * 60)
    print("🎉 Setup completed! Check the automation page for recent activities.")
