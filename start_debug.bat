@echo off
echo ================================================
echo        FiFTO Debug Server
echo ================================================
echo.
echo DEBUG MODE: Watch this terminal for debug output
echo when you click the "Generate Chart" button
echo.
echo 1. Open browser: http://127.0.0.1:8000/
echo 2. Click "Generate Chart" button
echo 3. Watch this terminal for debug messages
echo.
echo Press Ctrl+C to stop server
echo ================================================
echo.

python manage.py runserver 8000

pause
