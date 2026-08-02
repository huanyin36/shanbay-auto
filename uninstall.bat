@echo off
echo Removing scheduled task ShanbayDaily...
schtasks /Delete /TN "ShanbayDaily" /F >nul 2>nul
if errorlevel 1 (
    echo [WARN] Task not found or already removed.
) else (
    echo [OK] Task ShanbayDaily removed.
)
pause
