# ==============================================================================
# Xray Config Bench — Windows PowerShell Launcher
# ==============================================================================

[CmdletBinding()]
param (
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== Xray Config Bench (Windows) ===" -ForegroundColor Cyan

# Locate Python executable
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py -3"
} else {
    Write-Host "[ERROR] Python 3 was not found in PATH." -ForegroundColor Red
    Write-Host "Please download Python 3 from https://www.python.org/downloads/ and check 'Add Python to PATH'."
    Read-Host "Press Enter to exit"
    exit 1
}

$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvActivate = Join-Path $VenvDir "Scripts\Activate.ps1"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[*] Creating virtual environment in .venv..." -ForegroundColor Yellow
    Invoke-Expression "$PythonCmd -m venv `"$VenvDir`""
    
    Write-Host "[*] Upgrading pip and installing dependencies..." -ForegroundColor Yellow
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt")
}

Write-Host "[*] Launching Xray Config Bench..." -ForegroundColor Green
& $VenvPython (Join-Path $ScriptDir "main.py") @AppArgs
