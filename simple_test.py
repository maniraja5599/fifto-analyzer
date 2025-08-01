import os
import json

# Test the settings file functionality directly
def test_settings():
    print("Testing settings functionality...")
    
    # Define file paths
    home_dir = os.path.expanduser('~')
    settings_file = os.path.join(home_dir, "app_settings.json")
    
    print(f"Home directory: {home_dir}")
    print(f"Settings file path: {settings_file}")
    
    # Test 1: Create test settings
    test_settings = {
        'update_interval': '30 Mins',
        'bot_token': 'test_bot_token_123',
        'chat_id': 'test_chat_id_456'
    }
    
    # Test 2: Write to file
    try:
        with open(settings_file, 'w') as f:
            json.dump(test_settings, f, indent=2)
        print("✓ Settings file created successfully")
    except Exception as e:
        print(f"✗ Error creating settings file: {e}")
        return
    
    # Test 3: Check if file exists
    if os.path.exists(settings_file):
        print("✓ Settings file exists")
        
        # Test 4: Read back the content
        try:
            with open(settings_file, 'r') as f:
                loaded_settings = json.load(f)
            print(f"✓ Settings loaded: {loaded_settings}")
        except Exception as e:
            print(f"✗ Error reading settings: {e}")
    else:
        print("✗ Settings file does not exist")
    
    # Test 5: Check file permissions
    try:
        # Try to write again to check permissions
        with open(settings_file, 'a') as f:
            pass
        print("✓ File has write permissions")
    except Exception as e:
        print(f"✗ File permission error: {e}")

if __name__ == "__main__":
    test_settings()
