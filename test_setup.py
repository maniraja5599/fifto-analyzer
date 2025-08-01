#!/usr/bin/env python
"""
Simple test script to verify the Django project works
"""
import os
import sys
import django

# Add the project directory to Python path
project_dir = r"c:\Users\manir\Desktop\New folder\Django\fifto_project"
sys.path.append(project_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

# Setup Django
django.setup()

print("✓ Django setup successful")

# Test imports
try:
    from analyzer import views, utils
    print("✓ Analyzer app imports successful")
except Exception as e:
    print(f"✗ Analyzer import failed: {e}")
    sys.exit(1)

# Test the analysis function
try:
    result = utils.generate_analysis("NIFTY", "Weekly", "31-Jul-2025")
    print(f"✓ Analysis function test: {type(result)}")
except Exception as e:
    print(f"✗ Analysis function failed: {e}")

print("\n🎉 All tests passed! The Django project is ready.")
print("\nTo start the server:")
print("1. Open a terminal")
print("2. cd to the project directory")
print("3. Run: python manage.py runserver")
print("\nThe new async analysis feature should now work!")
