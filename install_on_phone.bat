@echo off
title Install NeonTrack APK on Phone
echo =======================================================
echo     Installing NeonTrack.apk to connected Android Phone
echo =======================================================
echo.
echo Waiting for device with USB debugging enabled...
echo (If prompted on your phone screen, tap "Allow USB Debugging")
echo.
"C:\Android\platform-tools\adb.exe" wait-for-device
echo [+] Device connected! Installing NeonTrack.apk...
"C:\Android\platform-tools\adb.exe" install -r -d "NeonTrack.apk"
if %errorlevel% equ 0 (
    echo.
    echo =======================================================
    echo [OK] SUCCESS: NeonTrack installed successfully!
    echo =======================================================
    echo Launching NeonTrack on your phone...
    "C:\Android\platform-tools\adb.exe" shell am start -n com.neontrack.mouse/.MainActivity
) else (
    echo.
    echo [-] Installation failed. Please check phone screen and retry.
)
pause
