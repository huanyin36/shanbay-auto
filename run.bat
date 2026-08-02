@echo off
rem Prefer the Python launcher (py), fall back to python on PATH.
rem No pause here so the scheduled task can run unattended; see shanbay.log for output.
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 "%~dp0shanbay.py"
) else (
    python "%~dp0shanbay.py"
)
