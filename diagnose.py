#!/usr/bin/env python
"""
Simple test to identify the exact error
"""

import os
import sys
import django
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

def test_imports():
    """Test all imports"""
    try:
        print("Testing Django...")
        import django
        print(f"✅ Django {django.get_version()} OK")
        
        print("Testing analyzer app...")
        import analyzer
        print("✅ Analyzer app OK")
        
        print("Testing utils...")
        from analyzer import utils
        print("✅ Utils import OK")
        
        print("Testing views...")
        from analyzer import views  
        print("✅ Views import OK")
        
        print("Testing URLs...")
        from analyzer import urls
        print("✅ URLs import OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_django_check():
    """Test Django system check"""
    try:
        print("\nRunning Django system check...")
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'check'])
        print("✅ Django check passed")
        return True
    except Exception as e:
        print(f"❌ Django check failed: {e}")
        return False

def main():
    print("🔍 Diagnosing Django Issues")
    print("=" * 40)
    
    if test_imports():
        print("\n✅ All imports successful!")
        if test_django_check():
            print("\n🎉 Everything looks good! Ready to start server.")
            print("\nTo start server manually, run:")
            print("python manage.py runserver")
        else:
            print("\n❌ Django configuration issues found.")
    else:
        print("\n❌ Import issues found.")

if __name__ == "__main__":
    main()
