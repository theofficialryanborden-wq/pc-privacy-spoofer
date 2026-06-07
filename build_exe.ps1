#Requires -Version 5.1
<#
.SYNOPSIS
  Build the PC Privacy Spoofer GUI executable with PyInstaller.
.EXAMPLE
  .\build_exe.ps1
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $ProjectRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not on PATH."
    exit 1
}

Write-Host "Installing build dependencies..."
python -m pip install --upgrade pip pyinstaller | Out-Null
python -m pip install -e . | Out-Null

Write-Host "Building executable..."
python -m PyInstaller --noconfirm --clean (Join-Path $ProjectRoot "build\pc-privacy-spoofer.spec")

$exePath = Join-Path $ProjectRoot "dist\PC-Privacy-Spoofer.exe"
if (Test-Path $exePath) {
    Write-Host ""
    Write-Host "Build complete:" -ForegroundColor Green
    Write-Host "  $exePath"
    Write-Host ""
    Write-Host "Run the .exe as Administrator for spoof/restore operations."
} else {
    Write-Error "Build failed - executable not found at $exePath"
    exit 1
}
