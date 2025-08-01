# Manual Cleanup Guide for Django Project

## Files to Delete (Safe to Remove)

### 1. Test and Debug Files
- test_telegram.py
- test_setup.py
- test_settings.py
- test_restore.py
- test_new_implementation.py
- test_lot_sizes.py
- test_final.py
- test_direct.py
- test_debug_server.py
- test_complete.py
- create_defaults.py
- form_test.py
- quick_test.py
- simple_test.py
- start_and_test.py
- start_server.py
- diagnose.py
- django_test.py

### 2. Batch Files (All .bat files)
- LAUNCH_APP.bat
- RUN_SERVER.bat
- start_debug.bat
- start_new_server.bat
- start_server.bat
- start_simple.bat
- TEST_BUTTON.bat
- git_restore.bat
- cleanup.bat (after cleanup is done)

### 3. PowerShell Scripts (All .ps1 files)
- git_restore.ps1
- cleanup.ps1 (after cleanup is done)

### 4. Documentation Files
- CLOSED_TRADES_FIXES.md
- LOT_SIZE_IMPLEMENTATION.md
- NEW_IMPLEMENTATION_SUMMARY.md
- DEBUG_INSTRUCTIONS.txt
- GIT_RESTORATION_GUIDE.txt

### 5. Duplicate/Backup Files in analyzer/
- analyzer/utils_new.py
- analyzer/utils_clean.py
- analyzer/utils_final.py
- analyzer/views_new.py
- analyzer/views_clean.py
- analyzer/urls_new.py
- analyzer/urls_clean.py
- analyzer/tasks.py

### 6. Unused Files
- fifto_project/celery.py

### 7. Python Cache Directories (Entire folders)
- analyzer/__pycache__/
- fifto_project/__pycache__/
- analyzer/management/__pycache__/
- analyzer/management/commands/__pycache__/
- analyzer/migrations/__pycache__/

## Files to KEEP (Important for Django App)

### Core Application Files
- manage.py ✅
- requirements.txt ✅
- db.sqlite3 ✅
- .gitignore ✅

### Main Application Directory
- analyzer/
  - __init__.py ✅
  - admin.py ✅
  - apps.py ✅
  - models.py ✅
  - tests.py ✅
  - urls.py ✅
  - utils.py ✅
  - views.py ✅
  - management/ ✅
  - migrations/ ✅

### Django Project Settings
- fifto_project/
  - __init__.py ✅
  - asgi.py ✅
  - settings.py ✅
  - urls.py ✅
  - wsgi.py ✅

### Frontend Files
- templates/ ✅
- static/ ✅

### Development Environment
- .git/ ✅
- .venv/ ✅

## How to Clean Manually

### Option 1: Windows File Explorer
1. Navigate to your project folder
2. Select all the files listed in "Files to Delete" section
3. Press Delete key or right-click → Delete
4. Empty the Recycle Bin

### Option 2: Command Prompt
Open Command Prompt in your project directory and run:
```cmd
del test_*.py
del *debug*.py  
del *.bat
del *.ps1
del *.md
del *.txt
del analyzer\*_new.py
del analyzer\*_clean.py
del analyzer\*_final.py
del analyzer\tasks.py
del fifto_project\celery.py
rmdir /s /q analyzer\__pycache__
rmdir /s /q fifto_project\__pycache__
rmdir /s /q analyzer\management\__pycache__
rmdir /s /q analyzer\management\commands\__pycache__
rmdir /s /q analyzer\migrations\__pycache__
```

### Option 3: PowerShell
Open PowerShell in your project directory and run:
```powershell
Remove-Item test_*.py -Force
Remove-Item *debug*.py -Force  
Remove-Item *.bat -Force
Remove-Item *.ps1 -Force
Remove-Item *.md -Force
Remove-Item *.txt -Force
Remove-Item analyzer\*_new.py -Force
Remove-Item analyzer\*_clean.py -Force
Remove-Item analyzer\*_final.py -Force
Remove-Item analyzer\tasks.py -Force
Remove-Item fifto_project\celery.py -Force
Remove-Item -Recurse -Force analyzer\__pycache__
Remove-Item -Recurse -Force fifto_project\__pycache__
Remove-Item -Recurse -Force analyzer\management\__pycache__
Remove-Item -Recurse -Force analyzer\management\commands\__pycache__
Remove-Item -Recurse -Force analyzer\migrations\__pycache__
```

## After Cleanup

Your project directory should only contain:
```
fifto_project/
├── .git/
├── .venv/
├── analyzer/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   ├── utils.py
│   ├── views.py
│   ├── management/
│   └── migrations/
├── fifto_project/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── static/
├── templates/
├── .gitignore
├── db.sqlite3
├── manage.py
└── requirements.txt
```

## Benefits of Cleanup
- Reduced project size
- Cleaner directory structure
- No confusion with duplicate files
- Faster project loading
- Better organization
- Easier navigation

Your Django application will work exactly the same after cleanup, but with a much cleaner structure!
