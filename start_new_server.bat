@echo off
echo ================================================
echo       STARTING NEW CLEAN FIFTO IMPLEMENTATION
echo ================================================
echo.

echo Checking Python environment...
python --version
echo.

echo Checking Django installation...
python -c "import django; print('Django version:', django.get_version())"
echo.

echo Running Django system check...
python manage.py check
echo.

echo Starting Django development server...
echo Open your browser and go to: http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server
echo ================================================
python manage.py runserver
