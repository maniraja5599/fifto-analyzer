#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')
sys.path.append(r'c:\Users\manir\Desktop\New folder\Django\fifto_project')

django.setup()

from django.template.loader import get_template
from django.template import Context

try:
    # Test automation template
    automation_template = get_template('analyzer/automation.html')
    print("✓ Automation template loaded successfully")
    
    # Test settings template
    settings_template = get_template('analyzer/settings.html')
    print("✓ Settings template loaded successfully")
    
    print("\nAll templates are working correctly!")
    
except Exception as e:
    print(f"✗ Template error: {e}")
    import traceback
    traceback.print_exc()
