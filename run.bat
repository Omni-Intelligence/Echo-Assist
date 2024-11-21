@echo off

:: Check for admin privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run
) else (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -FilePath '%~dpnx0' -Verb RunAs"
    exit /b
)

:run
:: Run the app
cd /d %~dp0
python productivity_app.py
pause
