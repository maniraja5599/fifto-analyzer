#!/usr/bin/env python
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils

print("Testing Telegram settings functionality...")

# Test 1: Check current settings
print("\n1. Current settings:")
current_settings = utils.load_settings()
print(f"Settings: {current_settings}")

# Test 2: Test saving new values
print("\n2. Testing save functionality:")
test_settings = {
    'update_interval': '30 Mins',
    'bot_token': '7981319366:AAG4mfNVjIyRSehitfkxQTN9D63d1EJMaa8',
    'chat_id': '-1002639599677'
}

try:
    utils.save_settings(test_settings)
    print("✓ Settings saved successfully")
except Exception as e:
    print(f"✗ Error saving: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Verify by loading again
print("\n3. Verifying saved settings:")
reloaded = utils.load_settings()
print(f"Reloaded: {reloaded}")

if reloaded.get('bot_token') == test_settings['bot_token']:
    print("✓ Bot token saved correctly")
else:
    print("✗ Bot token not saved correctly")

if reloaded.get('chat_id') == test_settings['chat_id']:
    print("✓ Chat ID saved correctly")
else:
    print("✗ Chat ID not saved correctly")

# Test 4: Check file contents directly
print("\n4. Checking file contents:")
settings_file = os.path.join(os.path.expanduser('~'), 'app_settings.json')
print(f"Settings file path: {settings_file}")

if os.path.exists(settings_file):
    with open(settings_file, 'r') as f:
        content = f.read()
        print(f"File content:\n{content}")
else:
    print("Settings file does not exist!")

print("\nTest completed!")
