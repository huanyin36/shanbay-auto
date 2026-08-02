@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   shanbay-auto installer
echo ============================================

echo.
echo [1/3] Checking Python...
set "PY="
where py >nul 2>nul
if %errorlevel% equ 0 set "PY=py -3"
if not defined PY (
    where python >nul 2>nul
    if %errorlevel% equ 0 set "PY=python"
)
if not defined PY (
    echo [ERROR] Python not found.
    echo         Install from https://www.python.org and check "Add python.exe to PATH".
    pause
    exit /b 1
)
%PY% --version

echo.
echo [2/3] Installing dependencies...
%PY% -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo       System-wide install failed, retrying with --user...
    %PY% -m pip install --quiet --user -r requirements.txt
)
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)
echo [OK] Dependencies ready.

echo.
echo [3/3] Creating logon scheduled task...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_task.ps1"
if errorlevel 1 (
    echo [ERROR] Could not create scheduled task.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Done. It runs automatically at every logon.
echo   Test now : double-click run.bat
echo   Logs     : shanbay.log
echo   Uninstall: double-click uninstall.bat
echo ============================================
pause
