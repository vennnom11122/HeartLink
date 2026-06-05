$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Virtual environment not found. Create it first: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

Set-Location $ProjectRoot
& $Python -m app.main
