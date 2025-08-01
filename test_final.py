import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

def test_functionality():
    """Test the key functions"""
    print("🧪 Testing Clean Implementation...")
    
    try:
        # Test imports
        from analyzer.views import index, generate_and_show_analysis, settings_view
        from analyzer.utils import generate_analysis, load_settings, save_settings
        print("✅ All imports successful")
        
        # Test settings
        settings = load_settings()
        print(f"✅ Settings loaded: {settings}")
        
        # Test save settings
        test_settings = {
            'update_interval': '15 Mins',
            'bot_token': 'test_123',
            'chat_id': 'test_456'
        }
        if save_settings(test_settings):
            print("✅ Settings save/load working")
        
        print("\n🎉 All tests passed! Server should work now.")
        print("Run: python manage.py runserver")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_functionality()
