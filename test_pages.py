#!/usr/bin/env python
import os
import sys
import django
import requests
from django.test import Client

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
sys.path.append(r'c:\Users\manir\Desktop\New folder\Django\fifto_project')

django.setup()

try:
    # Test with Django test client
    client = Client()
    
    print("Testing automation page...")
    automation_response = client.get('/automation/')
    print(f"Automation page status: {automation_response.status_code}")
    if automation_response.status_code != 200:
        print(f"Automation error: {automation_response.content}")
    
    print("Testing settings page...")
    settings_response = client.get('/settings/')
    print(f"Settings page status: {settings_response.status_code}")
    if settings_response.status_code != 200:
        print(f"Settings error: {settings_response.content}")
    
    if automation_response.status_code == 200 and settings_response.status_code == 200:
        print("✓ Both pages are working correctly!")
    else:
        print("✗ Some pages have issues")
        
except Exception as e:
    print(f"✗ Error during testing: {e}")
    import traceback
    traceback.print_exc()
