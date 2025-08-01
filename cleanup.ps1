# Cleanup script for Django project
# This script removes unwanted files safely without affecting core code

Write-Host "Starting cleanup of unwanted files..." -ForegroundColor Green

# Remove Python cache directories
$cacheDirectories = @(
    "analyzer\__pycache__",
    "fifto_project\__pycache__",
    "analyzer\management\__pycache__",
    "analyzer\management\commands\__pycache__",
    "analyzer\migrations\__pycache__"
)

foreach ($dir in $cacheDirectories) {
    if (Test-Path $dir) {
        Remove-Item -Recurse -Force $dir
        Write-Host "Removed: $dir" -ForegroundColor Yellow
    }
}

# Remove test files
$testFiles = @(
    "test_*.py",
    "*debug*.py",
    "create_defaults.py",
    "form_test.py",
    "quick_test.py",
    "simple_test.py",
    "start_and_test.py",
    "start_server.py",
    "diagnose.py",
    "django_test.py"
)

foreach ($pattern in $testFiles) {
    $files = Get-ChildItem -Path . -Name $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        Remove-Item -Force $file
        Write-Host "Removed: $file" -ForegroundColor Yellow
    }
}

# Remove batch files
$batchFiles = Get-ChildItem -Path . -Name "*.bat" -ErrorAction SilentlyContinue
foreach ($file in $batchFiles) {
    Remove-Item -Force $file
    Write-Host "Removed: $file" -ForegroundColor Yellow
}

# Remove PowerShell scripts (except this one)
$psFiles = Get-ChildItem -Path . -Name "*.ps1" -ErrorAction SilentlyContinue
foreach ($file in $psFiles) {
    if ($file -ne "cleanup.ps1") {
        Remove-Item -Force $file
        Write-Host "Removed: $file" -ForegroundColor Yellow
    }
}

# Remove duplicate analyzer files
$duplicateFiles = @(
    "analyzer\utils_new.py",
    "analyzer\utils_clean.py",
    "analyzer\utils_final.py",
    "analyzer\views_new.py",
    "analyzer\views_clean.py",
    "analyzer\urls_new.py",
    "analyzer\urls_clean.py",
    "analyzer\tasks.py"
)

foreach ($file in $duplicateFiles) {
    if (Test-Path $file) {
        Remove-Item -Force $file
        Write-Host "Removed: $file" -ForegroundColor Yellow
    }
}

# Remove unused celery file
if (Test-Path "fifto_project\celery.py") {
    Remove-Item -Force "fifto_project\celery.py"
    Write-Host "Removed: fifto_project\celery.py" -ForegroundColor Yellow
}

# Remove documentation files (keeping only essential ones)
$docFiles = @(
    "CLOSED_TRADES_FIXES.md",
    "LOT_SIZE_IMPLEMENTATION.md",
    "NEW_IMPLEMENTATION_SUMMARY.md",
    "DEBUG_INSTRUCTIONS.txt",
    "GIT_RESTORATION_GUIDE.txt"
)

foreach ($file in $docFiles) {
    if (Test-Path $file) {
        Remove-Item -Force $file
        Write-Host "Removed: $file" -ForegroundColor Yellow
    }
}

Write-Host "Cleanup completed!" -ForegroundColor Green
Write-Host "Core application files preserved:" -ForegroundColor Cyan
Write-Host "- manage.py" -ForegroundColor White
Write-Host "- requirements.txt" -ForegroundColor White
Write-Host "- db.sqlite3" -ForegroundColor White
Write-Host "- analyzer/ (main app)" -ForegroundColor White
Write-Host "- fifto_project/ (settings)" -ForegroundColor White
Write-Host "- templates/" -ForegroundColor White
Write-Host "- static/" -ForegroundColor White
Write-Host "- .git/" -ForegroundColor White
Write-Host "- .venv/" -ForegroundColor White
