# Git Code Restoration PowerShell Script
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "           GIT CODE RESTORATION SCRIPT" -ForegroundColor Cyan  
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking Git Status..." -ForegroundColor Yellow
Write-Host ""

# Check if git is available
try {
    git --version | Out-Null
    Write-Host "✅ Git is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Git is not installed or not in PATH" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

Write-Host ""
Write-Host "=== CURRENT GIT STATUS ===" -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "=== RECENT COMMITS ===" -ForegroundColor Yellow
git log --oneline -10

Write-Host ""
Write-Host "=== REFLOG (Recent Actions) ===" -ForegroundColor Yellow
git reflog -10

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "            RESTORATION OPTIONS" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🔄 SAFE OPTIONS (Recommended):" -ForegroundColor Green
Write-Host "1. Backup current state and restore:"
Write-Host "   git branch backup-current" -ForegroundColor Gray
Write-Host "   git reset --hard HEAD~1" -ForegroundColor Gray
Write-Host ""

Write-Host "2. Restore specific files only:"
Write-Host "   git checkout HEAD~1 -- analyzer/views.py" -ForegroundColor Gray
Write-Host "   git checkout HEAD~1 -- analyzer/utils.py" -ForegroundColor Gray
Write-Host ""

Write-Host "⚠️  DESTRUCTIVE OPTIONS (Use with caution):" -ForegroundColor Yellow
Write-Host "3. Discard all uncommitted changes:"
Write-Host "   git checkout ." -ForegroundColor Gray
Write-Host ""

Write-Host "4. Reset to previous commit:"
Write-Host "   git reset --hard HEAD~1" -ForegroundColor Gray
Write-Host ""

Write-Host "5. Reset to yesterday:"
Write-Host "   git reset --hard HEAD@{yesterday}" -ForegroundColor Gray
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "1. Review the commit history above"
Write-Host "2. Choose the appropriate restoration method"
Write-Host "3. Run the commands manually in this terminal"
Write-Host "4. Test your application after restoration"
Write-Host ""

$choice = Read-Host "Would you like me to suggest the best option based on your situation? (y/n)"

if ($choice -eq "y" -or $choice -eq "Y") {
    Write-Host ""
    Write-Host "💡 RECOMMENDATION:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "For your case (debugging issues with Generate Chart button):"
    Write-Host "1. First, create a backup:" -ForegroundColor Green
    Write-Host "   git branch backup-debug-version" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Then restore to working state:" -ForegroundColor Green
    Write-Host "   git reset --hard HEAD~1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Test the application:" -ForegroundColor Green
    Write-Host "   python manage.py runserver" -ForegroundColor Gray
    Write-Host ""
    Write-Host "If you need the debug features back later, you can:" -ForegroundColor Blue
    Write-Host "   git checkout backup-debug-version" -ForegroundColor Gray
}

Write-Host ""
Read-Host "Press Enter to close"
