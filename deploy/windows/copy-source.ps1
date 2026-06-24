<#
.SYNOPSIS
  Copy the Blender-AI source code from a local directory (or network share)
  to the production install location, then run npm ci + build.

.PARAMETER SourceDir
  Where the source is on THIS machine, e.g. I:\Projects-2026\BlenderAiMaster

.PARAMETER DestDir
  Where to install on the SERVER, e.g. C:\blender-ai
  (we copy both the backend + frontend subtrees here)
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$SourceDir,
    [string]$DestDir = "C:\blender-ai"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $SourceDir)) { throw "Source dir not found: $SourceDir" }

$backendSrc  = Join-Path $SourceDir "website\Blender_AI_Master_H"
$frontendSrc = Join-Path $SourceDir "website\blender-ai-master"
$backendDst  = Join-Path $DestDir "api"
$frontendDst = Join-Path $DestDir "frontend"

foreach ($p in @($backendSrc, $frontendSrc)) {
    if (-not (Test-Path $p)) { throw "Missing: $p" }
}

New-Item -ItemType Directory -Path $DestDir -Force | Out-Null

# --- 1. Backend ---
Write-Host "[1/4] Copying backend..." -ForegroundColor Yellow
$exclude = @("node_modules", "data.db", "data.db-shm", "data.db-wal", "*.bak", "*.log", ".env", "certs\*.pfx")
# backend: include dist (so user doesn't have to build on the server)
robocopy $backendSrc $backendDst /MIR /XD node_modules /XF data.db data.db-shm data.db-wal "*.bak" "*.log" ".env" "*.pfx" 2>&1 | Out-Null
Write-Host "  → $backendDst" -ForegroundColor Green

# --- 2. Frontend (built dist only) ---
Write-Host "[2/4] Copying frontend dist..." -ForegroundColor Yellow
$feDist = Join-Path $frontendSrc "dist"
if (-not (Test-Path $feDist)) {
    throw "Frontend dist not found. Run 'npm run build' in $frontendSrc first."
}
if (Test-Path $frontendDst) { Remove-Item $frontendDst -Recurse -Force }
New-Item -ItemType Directory -Path $frontendDst -Force | Out-Null
Copy-Item "$feDist\*" $frontendDst -Recurse -Force
Write-Host "  → $frontendDst" -ForegroundColor Green

# --- 2b. Copy plugin's built zip for users to download from server ---
$srcPluginDist = Join-Path (Split-Path -Parent $backendSrc) "plugin\dist"
if (Test-Path $srcPluginDist) {
    $pluginZipDst = "C:\blender-ai\frontend\downloads"
    New-Item -ItemType Directory -Path $pluginZipDst -Force | Out-Null
    Copy-Item "$srcPluginDist\*.zip" $pluginZipDst -Force -ErrorAction SilentlyContinue
    Write-Host "  → plugin zip(s) at $pluginZipDst" -ForegroundColor Green
}

# --- 3. npm ci + build backend ---
Write-Host "[3/4] Installing backend dependencies..." -ForegroundColor Yellow
Push-Location $backendDst
try { npm ci --omit=dev --no-audit --no-fund } catch { npm ci --no-audit --no-fund }
Write-Host "[4/4] Building backend..." -ForegroundColor Yellow
npm run build
Pop-Location
Write-Host "  Built $backendDst\dist" -ForegroundColor Green

Write-Host ""
Write-Host "=== Source copied to $DestDir ===" -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  1. Edit $backendDst\.env (HUNYUAN_*, STRIPE_*, PORT=3001)"
Write-Host "  2. Run install-api-service.ps1 to register as Windows Service"
Write-Host "  3. Run install-nginx.ps1 to set up reverse proxy"
Write-Host "  4. Run import-cert.ps1 if you have a real DigiCert"
