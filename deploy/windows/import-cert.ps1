<#
.SYNOPSIS
  Copy a real DigiCert (or any CA-signed) cert for blender-ai.com into the
  server's cert dir and import it into the Local Machine store.

.PARAMETER PfxPath
  Path to a .pfx (PKCS#12) file containing the cert + private key.
  If you only have .pem + .key, run convert-pem-to-pfx.ps1 first.

.EXAMPLE
  .\import-cert.ps1 -PfxPath D:\transfer\blender-ai.com.pfx
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$PfxPath,
    [string]$CertDir = "C:\blender-ai\certs",
    [string]$CertPwd = $env:CERT_PFX_PASSWORD
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $PfxPath)) { throw "PFX not found: $PfxPath" }
if (-not $CertPwd) {
    $secure = Read-Host -Prompt "PFX password" -AsSecureString
    $CertPwd = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}

New-Item -ItemType Directory -Path $CertDir -Force | Out-Null

# 1. 导入到 Local Machine 个人存储
Write-Host "[1/3] Importing to LocalMachine\My store..." -ForegroundColor Yellow
$pfxBytes = [System.IO.File]::ReadAllBytes($PfxPath)
$pfxFlags = [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::MachineKeySet -bor `
            [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::PersistKeySet
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2(
    $pfxBytes, $CertPwd, $pfxFlags)
Write-Host "  Subject: $($cert.Subject)"
Write-Host "  Issuer:  $($cert.Issuer)"
Write-Host "  Valid:   $($cert.NotBefore) → $($cert.NotAfter)"

# 2. 导出成 PEM (供 nginx 使用)
Write-Host "[2/3] Exporting to PEM for nginx..." -ForegroundColor Yellow
$gitOpenssl = "C:\Program Files\Git\usr\bin\openssl.exe"
if (-not (Test-Path $gitOpenssl)) {
    # 找其他 openssl
    $gitOpenssl = (Get-Command openssl -ErrorAction SilentlyContinue).Source
    if (-not $gitOpenssl) { throw "openssl.exe not found in PATH or Git\usr\bin" }
}

$pemFile = "$CertDir\blender-ai.com.pem"
$keyFile = "$CertDir\blender-ai.com.key"

# 临时 PFX (无密码) 给 openssl
$tmpPfx = "$env:TEMP\blender-ai.pfx"
[System.IO.File]::WriteAllBytes($tmpPfx, $pfxBytes)
$tmpPwd = $CertPwd

& $gitOpenssl pkcs12 -in $tmpPfx -nocerts -nodes -passin "pass:$tmpPwd" -out $keyFile 2>&1 | Out-Null
& $gitOpenssl pkcs12 -in $tmpPfx -clcerts -nokeys -passin "pass:$tmpPwd" -out $pemFile 2>&1 | Out-Null
& $gitOpenssl pkcs12 -in $tmpPfx -cacerts -nokeys -chain -passin "pass:$tmpPwd" -out "$CertDir\ca-bundle.pem" 2>&1 | Out-Null

# 把中间 CA 拼到主证书后面 (nginx 需要完整 chain)
if (Test-Path "$CertDir\ca-bundle.pem") {
    Get-Content $pemFile, "$CertDir\ca-bundle.pem" | Set-Content "$CertDir\blender-ai.com.fullchain.pem"
    Copy-Item "$CertDir\blender-ai.com.fullchain.pem" $pemFile -Force
    Remove-Item "$CertDir\ca-bundle.pem" -ErrorAction SilentlyContinue
}

Remove-Item $tmpPfx -ErrorAction SilentlyContinue
Write-Host "  Wrote $pemFile" -ForegroundColor Green
Write-Host "  Wrote $keyFile" -ForegroundColor Green

# 3. 用 .NET 重新导入,确保私钥可被 IIS/nginx 读
Write-Host "[3/3] Importing cert with private key (LocalMachine\My)..." -ForegroundColor Yellow
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store(
    "My", "LocalMachine")
$store.Open("ReadWrite")
$store.Remove($cert) 2>$null
$store.Add($cert)
$store.Close()
Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Green

Write-Host ""
Write-Host "=== Cert installed ===" -ForegroundColor Green
Write-Host "PEM:    $pemFile"
Write-Host "KEY:    $keyFile"
Write-Host "Store:  Cert:\LocalMachine\My\$($cert.Thumbprint)"
Write-Host ""
Write-Host "Now restart nginx to pick up the new cert:" -ForegroundColor Cyan
Write-Host "  Restart-Service nginx"
