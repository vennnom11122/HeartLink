$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Virtual environment not found. Create it first: .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

Set-Location $ProjectRoot

docker compose up -d postgres redis
& $Python -m alembic upgrade head
& $Python scripts\seed_cities.py

Write-Output "Local services are ready. Now run: .\run_bot.ps1"
