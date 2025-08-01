#!/usr/bin/env python
import os
import json

# Create settings file with default Telegram values
settings_file = os.path.join(os.path.expanduser('~'), 'app_settings.json')
default_settings = {
    'update_interval': '15 Mins',
    'bot_token': '7981319366:AAG4mfNVjIyRSehitfkxQTN9D63d1EJMaa8',
    'chat_id': '-1002639599677'
}

print(f"Creating settings file at: {settings_file}")

try:
    with open(settings_file, 'w') as f:
        json.dump(default_settings, f, indent=4)
    print("✓ Settings file created successfully")
    
    # Verify the file was created
    with open(settings_file, 'r') as f:
        content = f.read()
        print("✓ File content verified:")
        print(content)
        
except Exception as e:
    print(f"✗ Error creating settings file: {e}")
