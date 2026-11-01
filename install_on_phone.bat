@echo off
title Install PCDeck APK on Phone
echo =======================================================
echo     Installing PCDeck.apk to connected Android Phone
echo =======================================================
echo.
echo Waiting for device with USB debugging enabled...
echo (If prompted on your phone screen, tap "Allow USB Debugging")
echo.
"C:\Android\platform-tools\adb.exe" wait-for-device
echo [+] Device connected! Installing PCDeck.apk...
"C:\Android\platform-tools\adb.exe" install -r -d "PCDeck.apk"
if %errorlevel% equ 0 (
    echo.
    echo =======================================================
    echo [OK] SUCCESS: PCDeck installed successfully!
    echo =======================================================
    echo Launching PCDeck on your phone...
    "C:\Android\platform-tools\adb.exe" shell am start -n com.neontrack.mouse/.MainActivity
) else (
    echo.
    echo [-] Installation failed. Please check phone screen and retry.
)
pause
