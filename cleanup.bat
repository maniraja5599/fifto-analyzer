@echo off
echo Starting cleanup of unwanted files...

echo Removing test files...
del /q test_*.py 2>nul
del /q *debug*.py 2>nul
del /q create_defaults.py 2>nul
del /q form_test.py 2>nul
del /q quick_test.py 2>nul
del /q simple_test.py 2>nul
del /q start_and_test.py 2>nul
del /q start_server.py 2>nul
del /q diagnose.py 2>nul
del /q django_test.py 2>nul

echo Removing batch files...
del /q *.bat 2>nul

echo Removing PowerShell scripts...
del /q *.ps1 2>nul

echo Removing documentation files...
del /q *.md 2>nul
del /q *.txt 2>nul

echo Removing duplicate analyzer files...
del /q analyzer\*_new.py 2>nul
del /q analyzer\*_clean.py 2>nul
del /q analyzer\*_final.py 2>nul
del /q analyzer\tasks.py 2>nul

echo Removing unused celery file...
del /q fifto_project\celery.py 2>nul

echo Removing Python cache directories...
rmdir /s /q analyzer\__pycache__ 2>nul
rmdir /s /q fifto_project\__pycache__ 2>nul
rmdir /s /q analyzer\management\__pycache__ 2>nul
rmdir /s /q analyzer\management\commands\__pycache__ 2>nul
rmdir /s /q analyzer\migrations\__pycache__ 2>nul

echo Cleanup completed!
echo.
echo Core application files preserved:
echo - manage.py
echo - requirements.txt  
echo - db.sqlite3
echo - analyzer/ (main app)
echo - fifto_project/ (settings)
echo - templates/
echo - static/
echo - .git/
echo - .venv/
echo.
echo Your Django application is now clean and ready to use!
pause
