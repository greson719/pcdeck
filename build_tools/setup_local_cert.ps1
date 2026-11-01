$subject = 'CN=EE1A7F1B-8959-4B69-B895-5E5FF21E385E'
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $subject } | Select-Object -First 1

if (-not $cert) {
    Write-Host "Creating new self-signed CodeSigning certificate..."
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject -CertStoreLocation Cert:\CurrentUser\My -KeyUsage DigitalSignature -FriendlyName "PCDeck Local Test"
}

Write-Host "Using Cert Thumbprint: $($cert.Thumbprint)"

# Add to CurrentUser\TrustedPeople
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPeople", "CurrentUser")
$store.Open("ReadWrite")
$store.Add($cert)
$store.Close()
Write-Host "[+] Installed certificate into Cert:\CurrentUser\TrustedPeople"

# Export to PFX for signtool
$pfxPass = ConvertTo-SecureString -String "PCDeck123" -Force -AsPlainText
$pfxPath = "$PSScriptRoot\PCDeckTest.pfx"
Export-PfxCertificate -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" -FilePath $pfxPath -Password $pfxPass | Out-Null
Write-Host "[+] Exported PFX to $pfxPath"

# Export CER file
$cerPath = "$PSScriptRoot\PCDeckTest.cer"
Export-Certificate -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" -FilePath $cerPath | Out-Null
Write-Host "[+] Exported CER to $cerPath"
