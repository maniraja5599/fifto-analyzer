#!/usr/bin/env python
import os
import sys
import django
from unittest.mock import Mock

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

from analyzer import utils, views
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore

print("Testing form submission simulation...")

# Create a mock request object
request = Mock()
request.method = 'POST'
request.POST = {
    'interval': '30 Mins',
    'bot_token': 'simulated_token_123',
    'chat_id': 'simulated_chat_456',
    'csrfmiddlewaretoken': 'test_token'
}

# Add messages and session support
session = SessionStore()
session.create()
request.session = session

# Add message storage
messages = FallbackStorage(request)
request._messages = messages

print(f"Simulated POST data: {dict(request.POST)}")

# Test the current settings before
print("\nBefore form submission:")
current_settings = utils.load_settings()
print(f"Current settings: {current_settings}")

# Simulate the settings_view POST handling manually
print("\nSimulating form submission...")

try:
    # Get form values like the view does
    interval = request.POST.get('interval')
    bot_token = request.POST.get('bot_token')
    chat_id = request.POST.get('chat_id')
    
    print(f"Extracted values - interval: {interval}, bot_token: {bot_token}, chat_id: {chat_id}")
    
    # Load and update settings
    current_settings = utils.load_settings()
    current_settings['update_interval'] = interval
    current_settings['bot_token'] = bot_token
    current_settings['chat_id'] = chat_id
    
    print(f"Settings to save: {current_settings}")
    
    # Save settings
    utils.save_settings(current_settings)
    print("✓ Settings saved successfully!")
    
    # Verify by loading again
    reloaded_settings = utils.load_settings()
    print(f"Reloaded settings: {reloaded_settings}")
    
    # Check if values were saved correctly
    if (reloaded_settings.get('bot_token') == 'simulated_token_123' and 
        reloaded_settings.get('chat_id') == 'simulated_chat_456'):
        print("✓ Form data was saved correctly!")
    else:
        print("✗ Form data was not saved correctly")
        
except Exception as e:
    print(f"✗ Error during simulation: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed!")
