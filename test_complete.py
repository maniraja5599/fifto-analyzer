#!/usr/bin/env python
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils

print("Testing Telegram messaging functionality...")

# Test 1: Check current settings
print("\n1. Current settings:")
current_settings = utils.load_settings()
print(f"Bot Token: {current_settings.get('bot_token', 'Not set')}")
print(f"Chat ID: {current_settings.get('chat_id', 'Not set')}")

# Test 2: Test simple message
print("\n2. Testing simple message:")
try:
    result = utils.send_telegram_message("🚀 Test message from FiFTO Analyzer!\n\nTelegram integration is working correctly!")
    print(f"Message result: {result}")
except Exception as e:
    print(f"Error sending message: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Test settings save/load cycle
print("\n3. Testing settings save/load:")
try:
    test_settings = {
        'update_interval': '30 Mins',
        'bot_token': '7981319366:AAG4mfNVjIyRSehitfkxQTN9D63d1EJMaa8',
        'chat_id': '-1002639599677'
    }
    
    utils.save_settings(test_settings)
    print("✓ Settings saved")
    
    reloaded = utils.load_settings()
    print(f"✓ Settings reloaded: {reloaded}")
    
    if reloaded.get('bot_token') == test_settings['bot_token']:
        print("✓ Bot token persistence verified")
    else:
        print("✗ Bot token not persisted correctly")
        
    if reloaded.get('chat_id') == test_settings['chat_id']:
        print("✓ Chat ID persistence verified")
    else:
        print("✗ Chat ID not persisted correctly")
        
except Exception as e:
    print(f"Error in settings test: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed!")
