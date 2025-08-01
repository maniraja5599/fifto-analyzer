@echo off
cls
echo ================================================
echo        STARTING CLEAN FIFTO IMPLEMENTATION  
echo ================================================
echo.

echo [1/4] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo [2/4] Checking Django...
python -c "import django; print('Django', django.get_version(), 'OK')"
if %errorlevel% neq 0 (
    echo ERROR: Django not working!
    pause
    exit /b 1
)

echo [3/4] Running Django checks...
python manage.py check
if %errorlevel% neq 0 (
    echo ERROR: Django configuration issues!
    pause
    exit /b 1
)

echo [4/4] Starting server...
echo.
echo ✅ Server starting at: http://127.0.0.1:8000
echo.
echo 🎯 Use the application:
echo    1. Open http://127.0.0.1:8000 in your browser
echo    2. Select NIFTY or BANKNIFTY
echo    3. Choose calculation type and expiry
echo    4. Click Generate Charts
echo.
echo Press Ctrl+C to stop the server
echo ================================================
python manage.py runserver
