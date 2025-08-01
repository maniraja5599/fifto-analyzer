#!/usr/bin/env python
import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

import django
django.setup()

# Now test the settings functionality
from analyzer import utils

print("Testing settings functionality...")

# Test 1: Load current settings
print("\n1. Loading current settings:")
current_settings = utils.load_settings()
print(f"Current settings: {current_settings}")

# Test 2: Save settings with test data
print("\n2. Saving test settings:")
test_settings = {
    'update_interval': '30 Mins',
    'bot_token': 'test_bot_token_123',
    'chat_id': 'test_chat_id_456'
}

try:
    utils.save_settings(test_settings)
    print("Settings saved successfully")
except Exception as e:
    print(f"Error saving settings: {e}")

# Test 3: Check if file was created
print("\n3. Checking if settings file exists:")
settings_file = os.path.join(os.path.expanduser('~'), "app_settings.json")
print(f"Settings file path: {settings_file}")
print(f"File exists: {os.path.exists(settings_file)}")

if os.path.exists(settings_file):
    with open(settings_file, 'r') as f:
        content = f.read()
        print(f"File content: {content}")

# Test 4: Load settings again to verify
print("\n4. Loading settings again to verify:")
reloaded_settings = utils.load_settings()
print(f"Reloaded settings: {reloaded_settings}")

print("\nTest completed!")
