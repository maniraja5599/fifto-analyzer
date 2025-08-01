#!/usr/bin/env python
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

# Now test the Django utils
try:
    from analyzer import utils
    
    print("Testing Django utils functions...")
    
    # Test 1: Load current settings
    print("\n1. Loading current settings:")
    current_settings = utils.load_settings()
    print(f"Loaded settings: {current_settings}")
    
    # Test 2: Save new settings
    print("\n2. Saving new settings:")
    new_settings = {
        'update_interval': '1 Hour',
        'bot_token': 'django_test_token_789',
        'chat_id': 'django_test_chat_101'
    }
    
    try:
        utils.save_settings(new_settings)
        print("✓ Settings saved successfully using Django utils")
    except Exception as e:
        print(f"✗ Error saving settings: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Load again to verify
    print("\n3. Loading settings again:")
    reloaded_settings = utils.load_settings()
    print(f"Reloaded settings: {reloaded_settings}")
    
    # Test 4: Check if the values match
    print("\n4. Verification:")
    if reloaded_settings == new_settings:
        print("✓ Settings save/load cycle works correctly!")
    else:
        print("✗ Settings don't match:")
        print(f"  Expected: {new_settings}")
        print(f"  Got:      {reloaded_settings}")

except Exception as e:
    print(f"Error importing or using Django utils: {e}")
    import traceback
    traceback.print_exc()
