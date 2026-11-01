@echo off
:: PCDeck Clean Uninstaller & Folder Purge Helper
:: Auto-elevates to Administrator to cleanly delete C:\Program Files\PCDeck and installed drivers
setlocal EnableDelayedExpansion

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Requesting Administrator privileges for full PCDeck cleanup...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo [*] Terminating any running PCDeck processes...
taskkill /F /IM PCDeck.exe >nul 2>&1
taskkill /F /FI "IMAGENAME eq PCDeck*" >nul 2>&1

echo [*] Removing Windows Defender Firewall rules...
netsh advfirewall firewall delete rule name="PCDeck" >nul 2>&1

echo [*] Removing autostart Scheduled Task...
schtasks /delete /tn "PCDeck" /f >nul 2>&1

echo [*] Unregistering DirectShow webcam filters...
regsvr32.exe /u /s "C:\Program Files\PCDeck\drivers\UnityCaptureFilter64.dll" >nul 2>&1
regsvr32.exe /u /s "C:\Program Files\PCDeck\drivers\UnityCaptureFilter32.dll" >nul 2>&1
regsvr32.exe /u /s "%~dp0drivers\UnityCaptureFilter64.dll" >nul 2>&1
regsvr32.exe /u /s "%~dp0drivers\UnityCaptureFilter32.dll" >nul 2>&1

echo [*] Uninstalling ViGEmBus driver if present...
if exist "C:\Program Files\PCDeck\drivers\ViGEmBus_x64.msi" (
    msiexec.exe /x "C:\Program Files\PCDeck\drivers\ViGEmBus_x64.msi" /qn /norestart >nul 2>&1
)
if exist "%~dp0drivers\ViGEmBus_x64.msi" (
    msiexec.exe /x "%~dp0drivers\ViGEmBus_x64.msi" /qn /norestart >nul 2>&1
)

echo [*] Running built-in uninstaller if present...
if exist "C:\Program Files\PCDeck\unins000.exe" (
    "C:\Program Files\PCDeck\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
)

echo [*] Removing desktop and start menu shortcuts...
del /f /q "%USERPROFILE%\Desktop\PCDeck.lnk" >nul 2>&1
del /f /q "%PUBLIC%\Desktop\PCDeck.lnk" >nul 2>&1
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\PCDeck.lnk" >nul 2>&1
del /f /q "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\PCDeck.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\pcdeck_pro_debug.log" >nul 2>&1

echo [*] Removing C:\Program Files\PCDeck directory completely...
if exist "C:\Program Files\PCDeck" (
    takeown /f "C:\Program Files\PCDeck" /r /d y >nul 2>&1
    icacls "C:\Program Files\PCDeck" /grant administrators:F /t >nul 2>&1
    rmdir /s /q "C:\Program Files\PCDeck" >nul 2>&1
)

if not exist "C:\Program Files\PCDeck" (
    echo [OK] SUCCESS: PCDeck and its driver folder have been completely removed!
) else (
    echo [!] Note: Some locked files could not be immediately deleted. A reboot may be required.
)

timeout /t 3 >nul
exit /b
