@echo off
:: Self-elevate to Administrator if not already elevated
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ========================================================
echo Fixing Wi-Fi Dongle Auto-Configuration...
echo ========================================================
echo.

netsh wlan set autoconfig enabled=yes interface="Wi-Fi"

echo.
echo Current WLAN Settings:
netsh wlan show autoconfig

echo.
echo Scanning for available Wi-Fi networks (waiting 3 seconds)...
timeout /t 3 /nobreak >nul
netsh wlan show networks

echo.
echo ========================================================
echo Completed! Check your Windows taskbar Wi-Fi menu now.
echo ========================================================
pause
