# ============================================================================
# ScreenLoupe — one-command release build (Phase 7)
# Usage:  .\scripts\build.ps1
# Output: dist\ScreenLoupe-Setup.exe
# Requires: pip install -e ".[dev]"; Inno Setup 6 (ISCC on PATH or default dir)
# ============================================================================
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")   # repo root

Write-Host "[1/4] Generating assets..." -ForegroundColor Cyan
py -3.13 scripts/generate_assets.py
if ($LASTEXITCODE -ne 0) { throw "Asset generation failed" }

Write-Host "[2/4] Cleaning previous build..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "[3/4] PyInstaller (--onedir, no console)..." -ForegroundColor Cyan
py -3.13 -m PyInstaller --noconfirm --onedir --noconsole `
    --name ScreenLoupe `
    --icon assets\icon.ico `
    --add-data "assets;assets" `
    --paths src `
    --hidden-import=keyboard `
    --hidden-import=keyboard._winkeyboard `
    --hidden-import=mss `
    --hidden-import=mss.windows `
    --collect-submodules screenloupe `
    src\screenloupe\__main__.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "[4/4] Inno Setup compile..." -ForegroundColor Cyan
$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $fallback = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $fallback) { $iscc = $fallback }
    else { throw "ISCC.exe not found. Install Inno Setup 6 or add it to PATH." }
}
& $iscc installer\screenloupe.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed" }

Write-Host "`nDone -> dist\ScreenLoupe-Setup.exe" -ForegroundColor Green
Write-Host "Verify on a clean VM: install, reboot, Alt+M magnify, uninstall (docs/04 Phase 7)." -ForegroundColor Yellow
