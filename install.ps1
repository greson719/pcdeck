# ==============================================================================
# PCDeck - Universal Emergency Windows Downloader & Launcher
# Usage: powershell -ExecutionPolicy Bypass -Command "irm https://pcdeck.vercel.app/install.ps1 | iex"
# ==============================================================================
$ErrorActionPreference = 'Stop'
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
} catch {}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  PCDeck Emergency Windows Downloader     " -ForegroundColor White
Write-Host "  No mouse required · Starting setup...   " -ForegroundColor DarkGray
Write-Host "==========================================" -ForegroundColor Cyan

$destDir = [System.IO.Path]::Combine($env:USERPROFILE, "Downloads")
if (-not (Test-Path -Path $destDir)) {
    $destDir = $env:TEMP
}
$destPath = [System.IO.Path]::Combine($destDir, "PCDeck.exe")

$urls = @(
    "https://github.com/greson719/pcdeck/releases/latest/download/PCDeck.exe",
    "https://pcdeck.vercel.app/PCDeck.exe"
)

$downloaded = $false
foreach ($url in $urls) {
    try {
        Write-Host "Downloading PCDeck.exe..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $url -OutFile $destPath -UseBasicParsing
        $downloaded = $true
        break
    } catch {
        Write-Warning "Failed downloading from $url. Trying next source..."
    }
}

if (-not $downloaded -or -not (Test-Path -Path $destPath)) {
    Write-Error "Failed to download PCDeck.exe. Please check your internet connection."
    exit 1
}

Write-Host "Download complete: $destPath" -ForegroundColor Green
Write-Host "Unblocking executable from Windows Defender filter..." -ForegroundColor DarkGray
try { Unblock-File -Path "$env:USERPROFILE\Downloads\PCDeck.exe" -ErrorAction SilentlyContinue } catch {}
try { Unblock-File -Path $destPath -ErrorAction SilentlyContinue } catch {}

Write-Host "Launching PCDeck.exe now..." -ForegroundColor Green
Start-Process -FilePath $destPath
