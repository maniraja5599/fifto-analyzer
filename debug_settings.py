#!/usr/bin/env python
"""
Debug Settings Loading
====================

Debug script to check what settings are being loaded.
"""

import os
import sys
import django
import json

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

def debug_settings():
    """Debug settings loading"""
    
    print("🔍 Debug Settings Loading")
    print("=" * 40)
    
    # Check settings file directly
    settings_file = os.path.join(project_root, 'fifto_settings.json')
    print(f"📁 Settings file: {settings_file}")
    print(f"📁 File exists: {os.path.exists(settings_file)}")
    
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            direct_settings = json.load(f)
        
        print(f"\n📋 Direct file contents:")
        print(f"   enable_live_trading: {direct_settings.get('enable_live_trading', 'NOT FOUND')}")
        print(f"   auto_place_orders: {direct_settings.get('auto_place_orders', 'NOT FOUND')}")
        print(f"   broker_accounts count: {len(direct_settings.get('broker_accounts', []))}")
    
    # Check via utils.load_settings
    try:
        from analyzer.utils import load_settings
        loaded_settings = load_settings()
        
        print(f"\n📋 Via load_settings():")
        print(f"   enable_live_trading: {loaded_settings.get('enable_live_trading', 'NOT FOUND')}")
        print(f"   auto_place_orders: {loaded_settings.get('auto_place_orders', 'NOT FOUND')}")
        print(f"   broker_accounts count: {len(loaded_settings.get('broker_accounts', []))}")
        
        # Show all keys in loaded settings
        print(f"\n🔑 All keys in loaded_settings:")
        for key in sorted(loaded_settings.keys()):
            print(f"   {key}: {loaded_settings[key]}")
            
    except Exception as e:
        print(f"❌ Error loading via utils: {e}")

if __name__ == '__main__':
    debug_settings()
