# start-https-local.ps1
# 在本机 8443 端口跑一个 HTTPS 反向代理,转发到 3000 (后端)
# 用于: 在本机用 https://localhost:8443 模拟 https://www.blender-ai.com:8443
#
# Usage:
#   .\scripts\start-https-local.ps1
#   .\scripts\start-https-local.ps1 -Port 8443 -Upstream 3100

param(
    [int]$Port = 8443,
    [string]$Upstream = "http://127.0.0.1:3000"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$proxyScript = Join-Path $scriptDir "https-proxy.mjs"

if (-not (Test-Path $proxyScript)) {
    Write-Host "[ERROR] 找不到 $proxyScript" -ForegroundColor Red
    exit 1
}

Write-Host "=== Local HTTPS Reverse Proxy ===" -ForegroundColor Cyan
Write-Host "  Listen:    https://0.0.0.0:$Port" -ForegroundColor White
Write-Host "  Upstream:  $Upstream" -ForegroundColor White
Write-Host ""
Write-Host "先确认后端在 $Upstream 运行。" -ForegroundColor Yellow
try {
    $healthUrl = "$Upstream/health"
    $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  ✓ $healthUrl → $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 后端未响应 $Upstream/health" -ForegroundColor Red
    Write-Host "    请先在另一个终端运行 .\scripts\dev-up.ps1 启动后端" -ForegroundColor Red
    Write-Host ""
    $ans = Read-Host "仍然继续? (y/N)"
    if ($ans -ne "y") { exit 1 }
}
Write-Host ""

$env:PORT = "$Port"
$env:UPSTREAM = $Upstream

node $proxyScript
