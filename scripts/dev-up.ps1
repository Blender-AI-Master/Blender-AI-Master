# dev-up.ps1 - One-command local dev environment startup
#
# Usage:  .\scripts\dev-up.ps1
# Effect: 启动 Blender-AI Master 本地后端 (port 3100 by default)
#         + 可选启动一个本地 HTTPS 代理 (port 8443) 用于模拟生产 URL
#
# 项目实际目录结构:
#   BlenderAiMaster\
#     plugin\            <-- Blender 插件代码
#       scripts\
#         dev-up.ps1     <-- 你正在运行的文件
#     website\
#       blender-ai-master\       <-- 前端 (Vite + React)
#       Blender_AI_Master_H\     <-- 后端 (Hono + Drizzle + SQLite)

$ErrorActionPreference = "Stop"
# 这个脚本在 plugin/scripts/,所以 repoRoot = ../../  (即 BlenderAiMaster/)
$repoRoot    = Resolve-Path (Join-Path (Join-Path $PSScriptRoot "..") "..")
$backendDir  = Join-Path $repoRoot "website\Blender_AI_Master_H"
$frontendDir = Join-Path $repoRoot "website\blender-ai-master"

if (-not (Test-Path $backendDir)) {
    Write-Host "[ERROR] 找不到后端目录: $backendDir" -ForegroundColor Red
    Write-Host "        请确认仓库结构正确 (plugin\ + website\blender-ai-master\ + website\Blender_AI_Master_H\)"
    exit 1
}

Write-Host "=== Blender-AI Local Dev Setup ===" -ForegroundColor Cyan
Write-Host "  Backend:  $backendDir" -ForegroundColor Gray
Write-Host ""

# 1. 安装后端依赖
Write-Host "[1/3] Installing backend dependencies..." -ForegroundColor Yellow
Push-Location $backendDir
try {
    if (Test-Path "package-lock.json") {
        npm ci --ignore-scripts --legacy-peer-deps 2>&1 | Out-Null
    } else {
        npm install --ignore-scripts --legacy-peer-deps 2>&1 | Out-Null
    }
} catch {
    npm install --ignore-scripts --legacy-peer-deps 2>&1 | Out-Null
}
Write-Host "  Backend deps OK" -ForegroundColor Green

# 2. 推送 schema + 灌入定价
Write-Host ""
Write-Host "[2/3] Setting up database schema + pricing..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env" -Force
        Write-Host "  Created .env from .env.example" -ForegroundColor Gray
    } elseif (Test-Path ".env.local") {
        Copy-Item ".env.local" ".env" -Force
        Write-Host "  Created .env from .env.local" -ForegroundColor Gray
    }
}
npm run db:push 2>$null | Out-Null
npm run db:seed 2>$null | Out-Null
Write-Host "  DB schema pushed + pricing seeded" -ForegroundColor Green
Pop-Location

# 3. 启动后端 (前台运行,Ctrl+C 停止)
Write-Host ""
Write-Host "[3/3] Starting backend (Ctrl+C to stop)..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Backend URL:  http://localhost:3000" -ForegroundColor White
Write-Host "  (port 3100 if your .env has PORT=3100)" -ForegroundColor Gray
Write-Host "  Health:       http://localhost:3000/health" -ForegroundColor White
Write-Host "  Plugin test:  set API Server = Local Dev in Blender" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Need an API key for testing? Run in another terminal:" -ForegroundColor Gray
Write-Host "  cd website\Blender_AI_Master_H" -ForegroundColor Gray
Write-Host "  npm run db:create-key -- --email you@example.com --topup 50" -ForegroundColor Gray
Write-Host ""
Write-Host "Want to simulate production HTTPS (https://www.blender-ai.com:8443)?" -ForegroundColor Gray
Write-Host "  Run scripts\start-https-local.ps1 in another terminal" -ForegroundColor Gray
Write-Host ""

Push-Location $backendDir
try {
    npm run dev
} finally {
    Pop-Location
}
