@echo off
echo [*] Building PCDeck Microsoft Store MSIX package...
uv run python tools\generate_msstore_assets.py
if %ERRORLEVEL% NEQ 0 (
    echo [!] Asset generation failed.
    exit /b %ERRORLEVEL%
)
uv run python tools\build_msix.py
if %ERRORLEVEL% NEQ 0 (
    echo [!] MSIX Packaging failed.
    exit /b %ERRORLEVEL%
)
uv run python tools\update_checksums.py
echo [OK] Done! PCDeck.msix is ready and website checksums updated.
