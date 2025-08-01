@echo off
echo ================================================
echo          FiFTO Django Application
echo ================================================
echo.
echo Starting Django development server...
echo Open your browser to: http://127.0.0.1:8000/
echo.
echo Press Ctrl+C to stop the server
echo ================================================
echo.

cd /d "c:\Users\manir\Desktop\New folder\Django\fifto_project"
python manage.py runserver 8000

pause
