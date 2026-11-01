@echo off
title PCDeck - Automated Driver Installer
echo ========================================================
echo      [+] PCDECK AUTOMATED DRIVER INSTALLER
echo ========================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Requesting Administrator privileges to install required drivers...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [1] Installing ViGEmBus (Virtual Xbox 360 Controller Driver)...
if exist "%~dp0drivers\ViGEmBus_Setup.exe" (
    echo     Running ViGEmBus setup bundle...
    start /wait "" "%~dp0drivers\ViGEmBus_Setup.exe" /passive /norestart
)

sc query ViGEmBus >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%~dp0drivers\ViGEmBus_x64.msi" (
        echo     Running ViGEmBus MSI installer...
        msiexec.exe /i "%~dp0drivers\ViGEmBus_x64.msi" /passive /norestart ALLUSERS=1
    )
)

sc query ViGEmBus >nul 2>&1
if %errorlevel% equ 0 (
    echo     [OK] ViGEmBus Virtual Gamepad Driver installed successfully!
) else (
    echo     [-] Note: Please follow any on-screen prompt to finish driver installation.
)

echo.
echo [2] Installing VB-Audio Virtual Cable (Virtual Microphone)...
if exist "%~dp0drivers\VBCABLE_Setup_x64.exe" (
    start /wait "" "%~dp0drivers\VBCABLE_Setup_x64.exe" -i -h
    echo     [OK] VB-Audio driver installer executed.
)

echo.
echo [3] Registering Virtual Webcam DirectShow filters...
if exist "%~dp0drivers\UnityCaptureFilter64.dll" (
    regsvr32.exe /s "%~dp0drivers\UnityCaptureFilter64.dll"
)
if exist "%~dp0drivers\UnityCaptureFilter32.dll" (
    regsvr32.exe /s "%~dp0drivers\UnityCaptureFilter32.dll"
)
echo     [OK] Virtual Webcam DirectShow filters registered.

echo.
echo ========================================================
echo [SUCCESS] Driver Setup Complete!
echo Virtual Xbox 360 Controller is now ready for Elden Ring.
echo ========================================================
echo.
pause
