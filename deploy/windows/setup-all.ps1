<#
.SYNOPSIS
  ONE-SHOT master installer for Blender-AI Master on Windows Server 2025.

.DESCRIPTION
  跑这一个脚本就把:
    1. 源码拷贝到 C:\blender-ai\  (从本目录的 BlenderAiMaster/)
    2. 后端 .env 创建好 (第一次,需要手动填密钥)
    3. npm ci + npm run build
    4. Node API 注册成 Windows Service (NSSM)
    5. nginx 下载 + 配置 + 注册服务 + 防火墙
    6. 证书导入 (如果有 PFX)

  Re-run safely: 每次跑都会先 stop + remove 已有的同名 service,再重建。

.PARAMETER SourceDir
  解压后的源码根目录 (含 BlenderAiMaster\ 子目录)。
  默认脚本所在目录的 ..\..\BlenderAiMaster\

.PARAMETER DestDir
  部署到哪。默认 C:\blender-ai

.PARAMETER SkipFrontend
  跳过前端部署 (如果只改后端)

.PARAMETER PfxPath
  如果你有 DigiCert 的 PFX,给完整路径;不传就用自签 cert (仅 dev)

.EXAMPLE
  # 最简: 全自动,自签 cert
  .\setup-all.ps1

  # 用真证书
  $env:CERT_PFX_PASSWORD = "pfx密码"
  .\setup-all.ps1 -PfxPath D:\transfer\blender-ai.com.pfx
#>
[CmdletBinding()]
param(
    [string]$SourceDir = "",
    [string]$DestDir   = "C:\blender-ai",
    [switch]$SkipFrontend,
    [string]$PfxPath   = ""
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $SourceDir) {
    # 默认假设 setup-all.ps1 在 deploy-package\ 下,源码在 ..\BlenderAiMaster\
    $SourceDir = Join-Path (Split-Path -Parent $here) "BlenderAiMaster"
    if (-not (Test-Path $SourceDir)) {
        throw "SourceDir not found: $SourceDir  (参数 -SourceDir 指明)"
    }
}
if (-not (Test-Path $SourceDir)) { throw "SourceDir not found: $SourceDir" }

function Step($n, $msg) { Write-Host "`n[$n/6] $msg" -ForegroundColor Cyan }
function Ok($msg)      { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Fail($msg)    { Write-Host "  ✗ $msg" -ForegroundColor Red; throw $msg }

Write-Host "==============================================="
Write-Host "  Blender-AI Master — Windows Install"
Write-Host "  Source: $SourceDir"
Write-Host "  Dest:   $DestDir"
Write-Host "  Frontend: $(if ($SkipFrontend) {'skip'} else {'install'})"
Write-Host "  Cert:   $(if ($PfxPath) {$PfxPath} else {'self-signed (dev only)'})"
Write-Host "==============================================="

# --- 1. Copy source -------------------------------------------------------
Step 1 "Copying source code to $DestDir ..."
& "$here\copy-source.ps1" -SourceDir $SourceDir -DestDir $DestDir
Ok "Source copied"

# --- 2. Backend .env ------------------------------------------------------
Step 2 "Setting up backend .env ..."
$backendDir = Join-Path $DestDir "api"
$envFile    = Join-Path $backendDir ".env"
if (-not (Test-Path $envFile)) {
    Fail ".env missing. copy-source.ps1 should have created it. Check $backendDir"
}
# 强制写生产关键项
$envContent = Get-Content $envFile -Raw
$patched = $envContent
if ($patched -notmatch "(?m)^NODE_ENV=") {
    $patched = $patched -replace "(?m)^", ""
    $patched = "NODE_ENV=production`n" + $patched
}
if ($patched -notmatch "(?m)^PORT=") {
    $patched += "`nPORT=3001"
}
if ($patched -notmatch "(?m)^PUBLIC_SITE_URL=") {
    $patched += "`nPUBLIC_SITE_URL=https://www.blender-ai.com"
}
if ($patched -notmatch "(?m)^CORS_ORIGINS=") {
    $patched += "`nCORS_ORIGINS=https://www.blender-ai.com,https://localhost:8443"
}
[System.IO.File]::WriteAllText($envFile, $patched, [System.Text.UTF8Encoding]::new($false))
Ok ".env patched (NODE_ENV=production, PORT=3001, PUBLIC_SITE_URL, CORS_ORIGINS)"

if ($patched -match "HUNYUAN_SECRET_ID=AKID\.\.\." -or $patched -notmatch "HUNYUAN_SECRET_ID=\S+") {
    Warn "你需要在 $envFile 填好 HUNYUAN_SECRET_ID / HUNYUAN_SECRET_KEY / STRIPE_SECRET_KEY 后再启动服务"
    Warn "按任意键继续 (会用空 key 启动,功能受限) ..."
    Read-Host
}

# --- 3. Install API service ----------------------------------------------
Step 3 "Installing Node API as Windows Service ..."
& "$here\install-api-service.ps1" -InstallDir $backendDir
Ok "API service installed"

# --- 4. Install nginx ----------------------------------------------------
Step 4 "Installing nginx reverse proxy ..."
$frontendDst = Join-Path $DestDir "frontend"
if ($SkipFrontend) { $frontendDst = "$DestDir\frontend-placeholder" }
& "$here\install-nginx.ps1" -FrontendDir $frontendDst
Ok "nginx installed"

# --- 5. Cert --------------------------------------------------------------
Step 5 "Setting up cert ..."
if ($PfxPath -and (Test-Path $PfxPath)) {
    & "$here\import-cert.ps1" -PfxPath $PfxPath
    Ok "Cert imported from $PfxPath"
    Restart-Service nginx
} else {
    Warn "No PFX provided — using self-signed cert (browser will warn, plugin works fine)"
    Warn "  Pass -PfxPath on next run to replace with DigiCert"
}
Ok "Cert done"

# --- 6. Verify ------------------------------------------------------------
Step 6 "Final verification ..."
Start-Sleep -Seconds 2
$apiHealth = (Invoke-WebRequest -Uri "http://127.0.0.1:3001/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue).Content
if ($apiHealth) { Ok "API: $apiHealth" } else { Warn "API not responding on :3001" }

$nginx8443 = try { (Invoke-WebRequest -Uri "https://127.0.0.1:8443/health" -UseBasicParsing -TimeoutSec 5 -SkipCertificateCheck).Content } catch { $null }
if ($nginx8443) { Ok "API via nginx: $nginx8443" } else { Warn "API not responding via :8443 (check nginx log)" }

$elapsed = (Get-Date) - $startTime
Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "  Install complete in $($elapsed.ToString('mm\:ss'))" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API Service: Get-Service blender-ai-api"
Write-Host "  nginx:       Get-Service nginx"
Write-Host "  Logs:        Get-Content C:\blender-ai\logs\api-stderr.log -Tail 30"
Write-Host ""
Write-Host "  Next: 填好 $envFile (HUNYUAN_*, STRIPE_*) 然后:"
Write-Host "         Restart-Service blender-ai-api"
Write-Host "         Restart-Service nginx"
Write-Host ""
