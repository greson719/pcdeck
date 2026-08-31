Add-Type -AssemblyName System.Drawing
[Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null

$lang = New-Object Windows.Globalization.Language("en-US")
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)

$transDir = Join-Path $HOME "Downloads\PCDeck_Transfers"
$files = Get-ChildItem -Path "$transDir\Screenshot_20260828*.png"

foreach ($f in $files) {
    if ($f.Name -like "*_1.png") { continue }
    Write-Host "=================================================================="
    Write-Host "FILE: $($f.Name)"
    Write-Host "=================================================================="
    
    $fileTask = [Windows.Storage.StorageFile]::GetFileFromPathAsync($f.FullName)
    $storageFile = $fileTask.GetAwaiter().GetResult()
    
    $streamTask = $storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    $stream = $streamTask.GetAwaiter().GetResult()
    
    $decoderTask = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
    $decoder = $decoderTask.GetAwaiter().GetResult()
    
    $bmpTask = $decoder.GetSoftwareBitmapAsync()
    $softwareBmp = $bmpTask.GetAwaiter().GetResult()
    
    $ocrTask = $engine.RecognizeAsync($softwareBmp)
    $ocrResult = $ocrTask.GetAwaiter().GetResult()
    
    Write-Host $ocrResult.Text
    Write-Host ""
}
