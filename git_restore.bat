@echo off
echo ================================================
echo           GIT CODE RESTORATION SCRIPT
echo ================================================
echo.
echo This script will help you restore your code to a previous working state.
echo.
echo IMPORTANT: This will show you options but won't make changes automatically.
echo You'll need to run the commands manually after reviewing them.
echo.
pause
echo.

echo === CHECKING GIT STATUS ===
git status
echo.

echo === RECENT COMMITS ===
git log --oneline -10
echo.

echo === REFLOG (ALL RECENT ACTIONS) ===
git reflog -10
echo.

echo ================================================
echo            RESTORATION OPTIONS
echo ================================================
echo.
echo Choose what you want to do:
echo.
echo 1. Discard all uncommitted changes (restore to last commit):
echo    git checkout .
echo.
echo 2. Reset to previous commit (DANGER: loses recent commits):
echo    git reset --hard HEAD~1
echo.
echo 3. Reset to 2 commits back:
echo    git reset --hard HEAD~2
echo.
echo 4. Reset to yesterday's state:
echo    git reset --hard HEAD@{yesterday}
echo.
echo 5. Restore specific files only:
echo    git checkout HEAD~1 -- analyzer/views.py
echo    git checkout HEAD~1 -- analyzer/utils.py
echo.
echo 6. Create backup branch first (RECOMMENDED):
echo    git branch backup-current
echo    git reset --hard HEAD~1
echo.
echo ================================================
echo.
echo Review the commit history above and choose the appropriate option.
echo Run the commands manually in this terminal.
echo.
pause
