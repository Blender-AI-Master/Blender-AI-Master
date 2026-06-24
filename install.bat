@echo off
REM ============================================================
REM CLI-Anything-Blender 一键安装脚本 (Windows / Blender 5.1.1)
REM 用法: 双击 install.bat,或在命令行运行 install.bat
REM ============================================================
chcp 65001 >nul
setlocal

set "SRC_DIR=%~dp0"
set "BL_USER_ADDONS=%APPDATA%\Blender Foundation\Blender\5.1\scripts\addons"
set "BL_SYS_ADDONS=C:\Program Files\Blender Foundation\Blender 5.1\5.1\scripts\addons"
set "TMP_ZIP=%TEMP%\cli_anything_blender_v3.zip"

echo ============================================================
echo  CLI-Anything-Blender 一键安装脚本
echo ============================================================
echo.

REM ---- 1. 清理用户目录下的旧残留 ----
echo [1/4] 清理残留 addons 目录...
for /d %%d in ("%BL_USER_ADDONS%\cli_anything_blender" "%BL_USER_ADDONS%\CLI_Anything_Blender" "%BL_USER_ADDONS%\cli_Anything_Blender") do (
    if exist "%%d" (
        echo   - 删除 %%d
        rd /s /q "%%d"
    )
)
if exist "%BL_USER_ADDONS%\AI-Assistant-for-Blender" (
    echo   - 删除 %BL_USER_ADDONS%\AI-Assistant-for-Blender
    rd /s /q "%BL_USER_ADDONS%\AI-Assistant-for-Blender"
)
echo.

REM ---- 2. 清理 Blender 持久化配置(消除旧 addons entry 缓存) ----
echo [2/4] 备份并清空 userpref.blend (消除旧 addons 缓存)...
if exist "%APPDATA%\Blender Foundation\Blender\5.1\config\userpref.blend" (
    copy /y "%APPDATA%\Blender Foundation\Blender\5.1\config\userpref.blend" "%APPDATA%\Blender Foundation\Blender\5.1\config\userpref.blend.bak" >nul
    del /q "%APPDATA%\Blender Foundation\Blender\5.1\config\userpref.blend"
    echo   - userpref.blend 已备份到 userpref.blend.bak 并删除
) else (
    echo   - userpref.blend 不存在,跳过
)
echo.

REM ---- 3. 打包 zip(根目录必须为 cli_anything_blender/) ----
echo [3/4] 打包 addons 为 zip...
if exist "%TMP_ZIP%" del /q "%TMP_ZIP%"

REM 用 PowerShell + Python zipfile 打包(排除不必要的目录)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Add-Type -AssemblyName System.IO.Compression.FileSystem; ^
     $src = '%SRC_DIR%'; ^
     $dst = '%TMP_ZIP%'; ^
     $excludeDirs = @('.git','__pycache__','tools','output','opencode_bin','sdk_wheels','skills','Foundation','.opencode','cli_anything','resources','config'); ^
     $excludeFiles = @('.gitignore'); ^
     if (Test-Path $dst) { Remove-Item $dst }; ^
     $zip = [System.IO.Compression.ZipFile]::Open($dst, [System.IO.Compression.ZipArchiveMode]::Create); ^
     $rootName = 'cli_anything_blender'; ^
     foreach ($item in Get-ChildItem -LiteralPath $src -Recurse -File) { ^
         $rel = $item.FullName.Substring($src.Length).TrimStart('\','/'); ^
         $topDir = ($rel -split '[\\/]')[0]; ^
         if ($excludeDirs -contains $topDir) { continue }; ^
         if ($excludeFiles -contains $item.Name) { continue }; ^
         if ($item.Name -like '*.pyc') { continue }; ^
         $arc = $rootName + '/' + ($rel -replace '\\','/'); ^
         [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $item.FullName, $arc, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null; ^
     }; ^
     $zip.Dispose(); ^
     Write-Host ('  - zip 大小: ' + (Get-Item $dst).Length + ' bytes')"
if not exist "%TMP_ZIP%" (
    echo [ERROR] 打包失败
    pause
    exit /b 1
)
echo.

REM ---- 4. 让 Blender 加载并启用 ----
echo [4/4] 用 Blender 加载并启用 addons...
set "BL_EXE=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
if not exist "%BL_EXE%" (
    echo [ERROR] 找不到 Blender: %BL_EXE%
    echo   请修改 install.bat 中的 BL_EXE 路径
    pause
    exit /b 1
)

"%BL_EXE%" --background --python-exit-code 1 --python "%~dp0tools\install_headless.py" -- "%TMP_ZIP%" || (
    echo [ERROR] Blender 安装失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  安装完成!
echo ============================================================
echo.
echo  接下来:
echo   1. 完全关闭 Blender 5.1
echo   2. 重新打开 Blender 5.1
echo   3. Edit ^> Preferences ^> Extensions
echo   4. 找到 "AI Assistant for Blender" 并勾选启用
echo.
pause
