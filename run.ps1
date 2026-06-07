#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Launch PC Privacy Spoofer with admin privileges.
.EXAMPLE
  .\run.ps1 status
  .\run.ps1 spoof --all
  .\run.ps1 restore
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Env:PYTHONPATH = Join-Path $ProjectRoot "src"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not on PATH."
    exit 1
}

python -m privacy_spoofer @Args
