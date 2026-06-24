# build-plugin.ps1 - Build Blender plugin zip for distribution
# Usage: .\scripts\build-plugin.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$zipPath = Join-Path $root "dist"
$zipFile = Join-Path $zipPath "blender-ai-assistant-2.6.0.zip"

if (-not (Test-Path $zipPath)) {
    New-Item -ItemType Directory -Path $zipPath -Force | Out-Null
}

$tmp = Join-Path $env:TEMP "aiai-build-$(Get-Random)"
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

$items = @(
    "__init__.py",
    "blender_manifest.toml",
    "branding.py",
    "i18n.py",
    "api",
    "core",
    "cli_anything",
    "utils",
    "resources",
    "sdk_wheels"
)

# Blender 5.1 manifest format requires cli_anything_blender/ as the zip root.
$addonRoot = Join-Path $tmp "cli_anything_blender"
New-Item -ItemType Directory -Path $addonRoot -Force | Out-Null

foreach ($item in $items) {
    $src = Join-Path $root $item
    $dst = Join-Path $addonRoot $item
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Recurse -Force
    }
}

Get-ChildItem -Path $tmp -Recurse -Include "__pycache__", ".DS_Store", "*.pyc", "*.pyo" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$backendGitKeep = Join-Path $tmp "backend"
if (Test-Path $backendGitKeep) {
    Remove-Item -Path $backendGitKeep -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

Compress-Archive -Path "$tmp\*" -DestinationPath $zipFile -Force
Remove-Item -Path $tmp -Recurse -Force

$size = [math]::Round((Get-Item $zipFile).Length / 1MB, 2)
Write-Host ""
Write-Host "Build complete: $zipFile" -ForegroundColor Green
Write-Host "  Size: $size MB"
Write-Host ""
Write-Host "To install:" -ForegroundColor Yellow
Write-Host "  Blender > Edit > Preferences > Extensions > Install"
Write-Host "  Select: $zipFile"
