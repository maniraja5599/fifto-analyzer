#!/usr/bin/env python3
"""
Test script for dashboard headers in all pages
"""
import os
import django
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from django.test import Client

def test_dashboard_headers():
    print("🎨 Testing all pages with dashboard headers...")
    client = Client()
    
    # Test pages
    pages = [
        ('/', 'Home/Index'),
        ('/automation/', 'Automation Center'),
        ('/trades/', 'Active Trades'),
        ('/closed-trades/', 'Closed Trades'),
        ('/settings/', 'Settings')
    ]
    
    results = []
    for url, page_name in pages:
        try:
            response = client.get(url)
            if response.status_code == 200:
                print(f'✅ {page_name}: Status {response.status_code} - OK')
                results.append(f'✅ {page_name}: Working')
            else:
                print(f'❌ {page_name}: Status {response.status_code} - Error')
                results.append(f'❌ {page_name}: Error {response.status_code}')
        except Exception as e:
            print(f'❌ {page_name}: Exception - {e}')
            results.append(f'❌ {page_name}: Exception')
    
    print('\n🎉 Dashboard header test complete!')
    print('\nSummary:')
    for result in results:
        print(result)

if __name__ == '__main__':
    test_dashboard_headers()
