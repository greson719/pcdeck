@echo off
title PCDeck - Driver Uninstaller
echo ========================================================
echo      [+] PCDECK DRIVER UNINSTALLER (TESTING MODE)
echo ========================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Requesting Administrator privileges to uninstall drivers...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [1] Unregistering UnityCapture Virtual Webcam DirectShow filters...
if exist "%~dp0drivers\UnityCaptureFilter64.dll" (
    regsvr32.exe /u /s "%~dp0drivers\UnityCaptureFilter64.dll"
)
if exist "%~dp0drivers\UnityCaptureFilter32.dll" (
    regsvr32.exe /u /s "%~dp0drivers\UnityCaptureFilter32.dll"
)
echo     [OK] Virtual Webcam unregistered from DirectShow.

echo.
echo [2] Uninstalling VB-Audio Virtual Cable (Virtual Microphone)...
if exist "%~dp0drivers\VBCABLE_Setup_x64.exe" (
    start /wait "" "%~dp0drivers\VBCABLE_Setup_x64.exe" -u -h
    echo     [OK] VB-Audio driver uninstaller executed.
)
pnputil /remove-device "ROOT\MEDIA\0000" /force >nul 2>&1
for /f "tokens=1,2 delims=:" %%a in ('pnputil /enum-drivers ^| findstr /i "vbmmecable"') do (
    pnputil /delete-driver %%b /uninstall /force >nul 2>&1
)
echo     [OK] Virtual Audio device cleaned up.

echo.
echo [3] Checking ViGEmBus Gamepad Driver...
if exist "%~dp0drivers\ViGEmBus_Setup.exe" (
    start /wait "" "%~dp0drivers\ViGEmBus_Setup.exe" /uninstall /quiet
    echo     [OK] ViGEmBus uninstaller executed.
)

echo.
echo ========================================================
echo [SUCCESS] All PCDeck drivers have been uninstalled!
echo You can now test the fresh driver installation flow in PCDeck.
echo ========================================================
echo.
pause
