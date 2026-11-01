# Clear Windows Explorer Icon Cache
Write-Host "Restarting Explorer and refreshing icon cache..."

Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 1000

$localApp = [Environment]::GetFolderPath('LocalApplicationData')
$iconCache1 = Join-Path $localApp 'IconCache.db'
$explorerDir = Join-Path $localApp 'Microsoft\Windows\Explorer'

if (Test-Path $iconCache1) {
    Remove-Item -Path $iconCache1 -Force -ErrorAction SilentlyContinue
}

if (Test-Path $explorerDir) {
    Get-ChildItem -Path $explorerDir -Filter "iconcache*.db" -Force | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $explorerDir -Filter "thumbcache*.db" -Force | Remove-Item -Force -ErrorAction SilentlyContinue
}

Start-Process explorer.exe
Start-Sleep -Seconds 2

# Notify Windows Shell
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class ShellRefresh {
    [DllImport("shell32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
}
"@ -ErrorAction SilentlyContinue

try {
    [ShellRefresh]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {}

Write-Host "[OK] Windows Explorer icon cache successfully refreshed!"
