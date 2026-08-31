@echo off
setlocal enabledelayedexpansion
title NeonTrack - Wireless Debugging APK Installer
cls
echo ====================================================================
echo        NEONTRACK - WIRELESS DEBUGGING APK INSTALLER
echo ====================================================================
echo.
echo Please ensure your phone is on the SAME WI-FI network as this PC.
echo.
echo On your Android phone:
echo   1. Go to Settings -^> Developer options
echo   2. Enable "Wireless debugging"
echo.

set /p HAS_PAIRED="Have you paired this PC with the phone before? (y/n) [Default: n]: "
if /i "%HAS_PAIRED%"=="y" goto CONNECT_DIRECT

:PAIR_FLOW
echo.
echo --------------------------------------------------------------------
echo STEP 1: PAIRING YOUR PHONE
echo --------------------------------------------------------------------
echo On your phone, tap on "Pair device with pairing code"
echo.
set /p PAIR_ADDR="Enter the IP & Port shown on phone (e.g. 192.168.1.5:38421): "
set /p PAIR_CODE="Enter the 6-digit Wi-Fi pairing code shown on phone: "

echo.
echo [*] Pairing device at %PAIR_ADDR% with code %PAIR_CODE%...
adb pair %PAIR_ADDR% %PAIR_CODE%
if %errorlevel% neq 0 (
    echo.
    echo [-] Pairing failed. Please check the code and IP/Port and try again.
    pause
    exit /b 1
)
echo [+] Pairing successful!

:CONNECT_DIRECT
echo.
echo --------------------------------------------------------------------
echo STEP 2: CONNECTING WIRELESS DEBUGGING
echo --------------------------------------------------------------------
echo Look at the main "Wireless debugging" screen on your phone.
echo Under "IP address & Port", find the connection port.
echo.
set /p CONN_ADDR="Enter the main IP & Port shown on phone (e.g. 192.168.1.5:41235): "

echo.
echo [*] Connecting to %CONN_ADDR%...
adb connect %CONN_ADDR%
timeout /t 2 >nul

adb devices
echo.
echo [*] Installing NeonTrack.apk wirelessly...
adb install -r -d "NeonTrack.apk"
if %errorlevel% equ 0 (
    echo.
    echo ====================================================================
    echo [OK] SUCCESS: NeonTrack installed wirelessly on your phone!
    echo ====================================================================
    echo [*] Launching NeonTrack...
    adb shell am start -n com.neontrack.mouse/.MainActivity
) else (
    echo.
    echo [-] Wireless installation failed. Please check if device is authorized.
)

echo.
pause
