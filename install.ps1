# CLI-Anything-Blender one-click install script (Windows / Blender 5.1.1)
# Usage: Double-click install.ps1, or run in PowerShell: powershell -File install.ps1

$ErrorActionPreference = "Stop"

$ScriptPath = $MyInvocation.MyCommand.Path
if (-not $ScriptPath) { $ScriptPath = $PSCommandPath }
$SrcDir     = Split-Path -Parent $ScriptPath
$BlExe      = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$UserAddons = Join-Path $env:APPDATA "Blender Foundation\Blender\5.1\scripts\addons"
$TmpZip     = Join-Path $env:TEMP "cli_anything_blender_v3.zip"

Write-Host "============================================================"
Write-Host " CLI-Anything-Blender one-click install script"
Write-Host "============================================================"
Write-Host ""

# 1. Clean up leftovers in scripts/addons/
Write-Host "[1/5] Cleaning leftover addons directories..."
if (Test-Path $UserAddons) {
    Get-ChildItem -LiteralPath $UserAddons -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @("cli_anything_blender", "CLI_Anything_Blender", "cli_Anything_Blender", "AI-Assistant-for-Blender") } |
        ForEach-Object {
            Write-Host "  - Removing $($_.FullName)"
            Remove-Item -LiteralPath $_.FullName -Recurse -Force
        }
}
# Also clean extensions/ paths (Blender 5.1+ extension location)
$ExtPaths = @(
    (Join-Path $env:APPDATA "Blender Foundation\Blender\5.1\extensions\user_default\cli_anything_blender"),
    "C:\Program Files\Blender Foundation\Blender 5.1\5.1\extensions\user_default\cli_anything_blender"
)
foreach ($p in $ExtPaths) {
    if (Test-Path -LiteralPath $p) {
        Write-Host "  - Removing $p"
        Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Write-Host ""

# 2. Clean userpref.blend
Write-Host "[2/5] Backup and clear userpref.blend (clears old addons cache)..."
$UserPref = Join-Path $env:APPDATA "Blender Foundation\Blender\5.1\config\userpref.blend"
if (Test-Path -LiteralPath $UserPref) {
    Copy-Item -LiteralPath $UserPref -Destination "$UserPref.bak" -Force
    Remove-Item -LiteralPath $UserPref -Force
    Write-Host "  - userpref.blend backed up to userpref.blend.bak and removed"
} else {
    Write-Host "  - userpref.blend not found, skipping"
}
Write-Host ""

# 3. Build zip
Write-Host "[3/5] Building addons zip..."
if (Test-Path -LiteralPath $TmpZip) {
    Remove-Item -LiteralPath $TmpZip -Force
}

Add-Type -AssemblyName "System.IO.Compression"
Add-Type -AssemblyName "System.IO.Compression.FileSystem"

$ExcludeDirs = @('.git','__pycache__','tools','output','opencode_bin','sdk_wheels','skills','Foundation','.opencode','cli_anything','resources','config')
$ExcludeFiles = @('.gitignore')

$zip = [System.IO.Compression.ZipFile]::Open($TmpZip, [System.IO.Compression.ZipArchiveMode]::Create)
$RootName = "cli_anything_blender"

Get-ChildItem -LiteralPath $SrcDir -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($SrcDir.Length).TrimStart('\','/')
    $topDir = ($rel -split '[\\/]')[0]
    if ($ExcludeDirs -contains $topDir) { return }
    if ($ExcludeFiles -contains $_.Name) { return }
    if ($_.Name -like '*.pyc') { return }
    $arc = "$RootName/$($rel -replace '\\','/')"
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $arc, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
}
$zip.Dispose()
Write-Host "  - zip path: $TmpZip ($((Get-Item $TmpZip).Length) bytes)"
Write-Host ""

# 4. Blender install + enable (Python script handles license patching)
Write-Host "[4/5] Blender loading and enabling addons..."
if (-not (Test-Path -LiteralPath $BlExe)) {
    Write-Host "[ERROR] Cannot find Blender: $BlExe"
    Read-Host "Press Enter to exit"
    exit 1
}

& $BlExe --background --python "$SrcDir\tools\install_headless.py" -- $TmpZip
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Host "[ERROR] Blender install failed (exit code $ExitCode)"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# 5. Final verification
Write-Host "[5/5] Final verification..."
$InstalledManifest = Join-Path $UserAddons "cli_anything_blender\blender_manifest.toml"
if (Test-Path -LiteralPath $InstalledManifest) {
    $content = Get-Content -LiteralPath $InstalledManifest -Raw
    if ($content -match 'license\s*=') {
        Write-Host "  - Manifest has license field [OK]"
    } else {
        Write-Host "  - WARNING: license still missing!"
    }
}

Write-Host ""
Write-Host "============================================================"
Write-Host " Installation complete!"
Write-Host "============================================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Fully close Blender 5.1"
Write-Host "  2. Reopen Blender 5.1"
Write-Host "  3. Edit > Preferences > Extensions"
Write-Host "  4. Find 'AI Assistant for Blender' and enable it"
Write-Host ""
Read-Host "Press Enter to exit"
