@echo off
echo.
echo ================================================
echo       TESTING BUTTON FUNCTIONALITY
echo ================================================
echo.

echo Starting Django development server...
echo.
echo 🎯 TEST INSTRUCTIONS:
echo.
echo 1. Open browser: http://127.0.0.1:8000
echo 2. Select BANKNIFTY from dropdown
echo 3. Choose Weekly calculation type  
echo 4. Pick any expiry date (e.g., 28-Aug-2025)
echo 5. Click "Generate Charts" button
echo.
echo ✅ EXPECTED BEHAVIOR:
echo   - Button shows "Processing..." briefly
echo   - Page redirects and shows results
echo   - Button returns to normal state
echo.
echo ❌ IF BUTTON STAYS STUCK:
echo   - Check browser console for errors
echo   - Verify form submission is working
echo.
echo ================================================

python manage.py runserver
