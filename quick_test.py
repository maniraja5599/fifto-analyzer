import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
django.setup()

print("Testing imports...")
try:
    from analyzer.views import index, generate_charts, settings_view, trades_view
    print("✅ Views imported successfully")
    
    from analyzer.utils import generate_analysis, load_settings, save_settings
    print("✅ Utils imported successfully")
    
    print("\n🎉 All imports successful! Server should work now.")
    print("\nTo start the server:")
    print("python manage.py runserver")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
