<#
.SYNOPSIS
  Install backend dependencies without triggering native compilation.
  Copies the pre-built better-sqlite3 binary from vendor/ into node_modules/.

.DESCRIPTION
  The default `npm install` for better-sqlite3 tries to compile from source
  (needs Python + MSBuild). On Windows servers without those build tools,
  the install fails. This script:

  1. Runs `npm install --ignore-scripts` (no postinstall = no compile)
  2. Overwrites the empty better-sqlite3 build/ with our vendored prebuilt
  3. Result: a fully functional better-sqlite3 without any C++ toolchain

.PARAMETER BackendDir
  Path to backend (the directory with package.json). Default: auto-detect
  by looking for parent that has package.json with "better-sqlite3".
#>
[CmdletBinding()]
param(
    [string]$BackendDir = "",
    [string]$VendorDir  = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $VendorDir) {
    $VendorDir = Join-Path $here "vendor\better-sqlite3"
}
if (-not $BackendDir) {
    # 没传就从当前目录往上找 package.json (含 "name": "blender-ai-master-api")
    $cur = (Get-Location).Path
    while ($cur) {
        $pkg = Join-Path $cur "package.json"
        if ((Test-Path $pkg) -and ((Get-Content $pkg -Raw) -match '"blender-ai-master-api"')) {
            $BackendDir = $cur
            break
        }
        $parent = Split-Path -Parent $cur
        if ($parent -eq $cur) { break }
        $cur = $parent
    }
}
if (-not $BackendDir) { throw "BackendDir not found (specify -BackendDir)" }
if (-not (Test-Path $VendorDir)) { throw "Vendor dir not found: $VendorDir" }
if (-not (Test-Path (Join-Path $VendorDir "build\Release\better_sqlite3.node"))) {
    throw "Vendor missing better_sqlite3.node at $VendorDir\build\Release\"
}

Write-Host "[1/3] Running npm install --ignore-scripts ..." -ForegroundColor Yellow
Push-Location $BackendDir
try {
    npm install --ignore-scripts --no-audit --no-fund 2>&1 | Out-Null
} finally {
    Pop-Location
}
Write-Host "  OK" -ForegroundColor Green

$bs3 = Join-Path $BackendDir "node_modules\better-sqlite3"
if (-not (Test-Path $bs3)) {
    throw "better-sqlite3 not in node_modules after npm install (dependency missing from package.json?)"
}

Write-Host "[2/3] Copying vendored prebuilt better_sqlite3.node ..." -ForegroundColor Yellow
# 删掉可能残留的 (npm install 留下的空 .node 占位)
Remove-Item "$bs3\build" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "$bs3\build\Release" -Force | Out-Null
Copy-Item (Join-Path $VendorDir "build\Release\*") "$bs3\build\Release\" -Force
Copy-Item (Join-Path $VendorDir "package.json") "$bs3\package.json" -Force
Copy-Item (Join-Path $VendorDir "lib\*") "$bs3\lib\" -Recurse -Force
Write-Host "  OK (size: $((Get-Item "$bs3\build\Release\better_sqlite3.node").Length) bytes)" -ForegroundColor Green

Write-Host "[3/3] Verifying better-sqlite3 loads ..." -ForegroundColor Yellow
$test = Push-Location $BackendDir
try {
    $r = node -e "const db=require('better-sqlite3')(':memory:'); console.log('OK', db.prepare('SELECT 1 AS a').get());" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "load failed: $r" }
    Write-Host "  $r" -ForegroundColor Green
} finally { Pop-Location }

Write-Host ""
Write-Host "=== Native deps installed without compiling ===" -ForegroundColor Green
