#!/usr/bin/env python
import os
import sys
import django
from django.test import Client

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
sys.path.append(r'c:\Users\manir\Desktop\New folder\Django\fifto_project')

django.setup()

try:
    print("🔍 Testing Django pages...")
    client = Client()
    
    # Test automation page
    print("Testing automation page...")
    automation_response = client.get('/automation/')
    print(f"✅ Automation page status: {automation_response.status_code}")
    
    # Test settings page
    print("Testing settings page...")
    settings_response = client.get('/settings/')
    print(f"✅ Settings page status: {settings_response.status_code}")
    
    if automation_response.status_code == 200 and settings_response.status_code == 200:
        print("\n🎉 SUCCESS: Both pages are working correctly!")
        print("✅ Automation page: WORKING")
        print("✅ Settings page: WORKING")
    else:
        print("\n❌ Some pages have issues")
        if automation_response.status_code != 200:
            print(f"Automation error: {automation_response.status_code}")
        if settings_response.status_code != 200:
            print(f"Settings error: {settings_response.status_code}")
        
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
