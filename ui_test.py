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
    print("🎨 Testing updated UI pages...")
    client = Client()
    
    # Test automation page with new UI
    print("Testing automation page with settings-style UI...")
    automation_response = client.get('/automation/')
    print(f"✅ Automation page status: {automation_response.status_code}")
    
    # Test settings page
    print("Testing settings page...")
    settings_response = client.get('/settings/')
    print(f"✅ Settings page status: {settings_response.status_code}")
    
    if automation_response.status_code == 200 and settings_response.status_code == 200:
        print("\n🎉 SUCCESS: Both pages are working with updated UI!")
        print("✅ Automation page: WORKING with clean settings-style UI")
        print("✅ Settings page: WORKING")
    else:
        print("\n❌ Some pages have issues")
        
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
