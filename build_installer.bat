@echo off
title PCDeck - Build Windows Installer
echo ========================================================
echo      [+] PCDECK AUTOMATED INSTALLER BUILDER
echo ========================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -u build_exe.py
) else (
    python -u build_exe.py
)
if %ERRORLEVEL% NEQ 0 (
    echo [!] Build failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [OK] Done! PCDeck-Setup.exe is ready in msstore_assets/ and website/.
pause
