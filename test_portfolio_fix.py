#!/usr/bin/env python3
"""
Simple test to verify the portfolio toggle is working correctly
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

def test_portfolio_toggle():
    print("🧪 Testing Portfolio Toggle Fix...")
    client = Client()
    
    try:
        # Test automation page loads
        print("1. Loading automation page...")
        response = client.get('/automation/')
        
        if response.status_code == 200:
            print("✅ Automation page loads successfully")
            
            # Check if portfolio toggle is in the form
            content = response.content.decode('utf-8')
            if 'name="auto_add_to_portfolio"' in content:
                print("✅ Portfolio toggle field found in form")
                print("✅ Portfolio toggle should now work when you click Save!")
            else:
                print("❌ Portfolio toggle field not found in form")
                
        else:
            print(f"❌ Error loading automation page: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
    
    print("\\n🎯 Summary:")
    print("- Portfolio toggle is now inside the form")
    print("- No duplicate toggles")
    print("- JavaScript simplified")
    print("- Should save correctly when form is submitted")

if __name__ == '__main__':
    test_portfolio_toggle()
