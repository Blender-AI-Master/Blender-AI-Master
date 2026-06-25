<#
.SYNOPSIS
  Install Blender-AI Master API as a Windows Service on Server 2025.

.DESCRIPTION
  - Installs NSSM (Non-Sucking Service Manager) if missing
  - Registers "blender-ai-api" service that runs the Node backend on :3001
  - Logs go to C:\blender-ai\logs\
  - Auto-restarts on crash

.PARAMETER InstallDir
  Where the backend code lives on the server. Default: C:\blender-ai\api

.PARAMETER NodeExe
  Path to node.exe. Default: C:\Program Files\nodejs\node.exe

.EXAMPLE
  .\install-api-service.ps1
  .\install-api-service.ps1 -InstallDir D:\apps\blender-ai\api
#>
[CmdletBinding()]
param(
    [string]$InstallDir  = "C:\blender-ai\api",
    [string]$NodeExe     = "C:\Program Files\nodejs\node.exe",
    [string]$ServiceName = "blender-ai-api",
    [int]$Port           = 3001
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $NodeExe)) { throw "Node not found: $NodeExe (install Node.js 20+ LTS first)" }
if (-not (Test-Path $InstallDir)) { throw "Backend dir not found: $InstallDir  (run copy-source.ps1 first)" }

# --- 1. NSSM ---------------------------------------------------------------
$NssmDir = "C:\Tools\nssm"
$NssmExe = "$NssmDir\nssm.exe"
if (-not (Test-Path $NssmExe)) {
    Write-Host "[1/4] NSSM not found, downloading..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $NssmDir -Force | Out-Null
    # 试多个源 (nssm.cc/release/ 经常 503):
    #   1) nssm.cc/ci/ - 官方 CI build,稳定
    #   2) github.com/dkxce/nssm - 社区维护的 fork v2.25
    $urls = @(
        "https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip"
        "https://github.com/dkxce/NSSM/releases/download/v2.25/NSSM_v2.25.zip"
    )
    $tmp = "$env:TEMP\nssm.zip"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $got = $false
    foreach ($url in $urls) {
        try {
            Write-Host "  试 $url ..." -ForegroundColor Gray
            Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -TimeoutSec 30
            $got = $true
            break
        } catch {
            Write-Host "  ✗ $url 失败: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    if (-not $got) { throw "NSSM 全部源都下不了,手动下放到 $NssmExe 后再跑" }
    Expand-Archive -Path $tmp -DestinationPath "$env:TEMP\nssm-extract" -Force
    # nssm zip contains win64/ and win32/ subfolders
    $win64 = Get-ChildItem "$env:TEMP\nssm-extract" -Recurse -Filter "nssm.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -like "*win64*" } | Select-Object -First 1
    if (-not $win64) {
        # dkxce fork 的 zip 是扁平结构,直接 nssm.exe 在根
        $win64 = Get-ChildItem "$env:TEMP\nssm-extract" -Recurse -Filter "nssm.exe" -ErrorAction SilentlyContinue |
            Where-Object { $_.DirectoryName -match "win64" -or $_.DirectoryName -match "amd64" } | Select-Object -First 1
        if (-not $win64) {
            $win64 = Get-ChildItem "$env:TEMP\nssm-extract" -Recurse -Filter "nssm.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        }
    }
    if (-not $win64) { throw "下载的 zip 里没找到 nssm.exe" }
    Copy-Item $win64.FullName $NssmExe -Force
    Remove-Item $tmp, "$env:TEMP\nssm-extract" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  Installed NSSM to $NssmExe" -ForegroundColor Green
} else {
    Write-Host "[1/4] NSSM already present at $NssmExe" -ForegroundColor Green
}

# --- 2. Logs dir ----------------------------------------------------------
$logDir = "C:\blender-ai\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

# --- 3. Build the .env if missing ----------------------------------------
$envFile = Join-Path $InstallDir ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $InstallDir ".env.example") $envFile -Force
    Write-Host "[2/4] Created $envFile from .env.example" -ForegroundColor Yellow
    Write-Host "      *** EDIT $envFile to set HUNYUAN_*, STRIPE_*, PORT=$Port ***" -ForegroundColor Red
} else {
    Write-Host "[2/4] .env already present" -ForegroundColor Green
}

# --- 4. Build dist if missing --------------------------------------------
$distIndex = Join-Path $InstallDir "dist\src\index.js"
if (-not (Test-Path $distIndex)) {
    Write-Host "[3/4] Building backend (npm run build)..." -ForegroundColor Yellow
    Push-Location $InstallDir
    try { npm ci; npm run build } finally { Pop-Location }
    Write-Host "  Built" -ForegroundColor Green
} else {
    Write-Host "[3/4] dist\index.js present" -ForegroundColor Green
}

# --- 5. Register service --------------------------------------------------
Write-Host "[4/4] Registering Windows Service '$ServiceName'..." -ForegroundColor Yellow
# 删旧的 (如果有)
if (Get-Service $ServiceName -ErrorAction SilentlyContinue) {
    & $NssmExe stop $ServiceName 2>$null
    & $NssmExe remove $ServiceName confirm
}

# 注册
& $NssmExe install $ServiceName $NodeExe
& $NssmExe set $ServiceName AppDirectory   $InstallDir
& $NssmExe set $ServiceName AppParameters  "--env-file=$envFile dist/src/index.js"
& $NssmExe set $ServiceName DisplayName    "Blender-AI Master API"
& $NssmExe set $ServiceName Description    "Node.js backend for Blender-AI Master plugin. Binds 127.0.0.1:$Port."
& $NssmExe set $ServiceName Start          SERVICE_AUTO_START
& $NssmExe set $ServiceName ObjectName     LocalSystem
& $NssmExe set $ServiceName Type           SERVICE_WIN32_OWN_PROCESS
& $NssmExe set $ServiceName AppStdout      "$logDir\api-stdout.log"
& $NssmExe set $ServiceName AppStderr      "$logDir\api-stderr.log"
& $NssmExe set $ServiceName AppRotateFiles 1
& $NssmExe set $ServiceName AppRotateBytes 10485760    # 10 MB
& $NssmExe set $ServiceName AppExit         Default Restart
& $NssmExe set $ServiceName AppRestartDelay 3000
& $NssmExe set $ServiceName ThrottleDelay   5000

# 启动
Start-Service $ServiceName
Start-Sleep -Seconds 3

# 验证
$svc = Get-Service $ServiceName
Write-Host "  Service status: $($svc.Status)" -ForegroundColor $(if ($svc.Status -eq 'Running') { 'Green' } else { 'Red' })
if ($svc.Status -ne 'Running') {
    Get-Content "$logDir\api-stderr.log" -ErrorAction SilentlyContinue | Select-Object -Last 20
    throw "Service failed to start"
}

# 探活
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "  Health check: $($r.StatusCode) $($r.Content)" -ForegroundColor Green
} catch {
    Write-Host "  Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Get-Content "$logDir\api-stderr.log" -ErrorAction SilentlyContinue | Select-Object -Last 20
}

Write-Host ""
Write-Host "=== Service '$ServiceName' installed and running ===" -ForegroundColor Green
Write-Host "Manage:" -ForegroundColor Cyan
Write-Host "  Start:   Start-Service $ServiceName"
Write-Host "  Stop:    Stop-Service  $ServiceName"
Write-Host "  Logs:    Get-Content $logDir\api-stdout.log -Wait"
Write-Host "  Remove:  & '$NssmExe' remove $ServiceName confirm"
