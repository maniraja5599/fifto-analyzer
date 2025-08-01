@echo off
echo ================================================
echo          FiFTO - Restored Simple Version
echo ================================================
echo.
echo Starting Django development server...
echo.
echo Changes made:
echo - Removed complex async/threading
echo - Restored simple form submissions  
echo - Removed AJAX JavaScript
echo - Simplified all views
echo.
echo Open browser to: http://127.0.0.1:8000/
echo.
echo Press Ctrl+C to stop the server
echo ================================================
echo.

python manage.py runserver 8000

pause
