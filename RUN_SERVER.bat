@echo off
cls
echo.
echo ================================================
echo          FIFTO ANALYZER - CLEAN VERSION
echo ================================================
echo.

echo [1/4] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found or not in PATH.
    pause
    exit /b 1
)

echo.
echo [2/4] Checking Django...
python -c "import django; print('Django', django.get_version(), 'OK')"
if %errorlevel% neq 0 (
    echo ERROR: Django is not installed or the virtual environment is not active.
    pause
    exit /b 1
)

echo.
echo [3/4] Running system check...
python manage.py check
if %errorlevel% neq 0 (
    echo ERROR: Django system check failed. Please review the errors above.
    pause
    exit /b 1
)

echo.
echo [4/4] Starting development server...
echo.
echo ✅ Server starting at: http://127.0.0.1:8000
echo.
echo 🎯 Open your browser and navigate to the URL above.
echo.
echo Press Ctrl+C in this window to stop the server.
echo ================================================
python manage.py runserver
