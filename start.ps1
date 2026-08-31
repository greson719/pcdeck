Write-Host "Starting PCDeck PC Server..." -ForegroundColor Cyan
if (Test-Path "PCDeck.exe") {
    Start-Process ".\PCDeck.exe"
} else {
    python server/gui.py
}

