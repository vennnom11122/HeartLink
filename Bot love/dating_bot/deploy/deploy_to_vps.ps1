param(
    [Parameter(Mandatory = $true)]
    [string]$Target,

    [string]$RemoteDir = "~/dating_bot"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Archive = Join-Path $env:TEMP "dating_bot_deploy.tar.gz"

Set-Location $ProjectRoot

if (Test-Path $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}

tar `
    --exclude ".venv" `
    --exclude ".env" `
    --exclude "__pycache__" `
    --exclude ".pytest_cache" `
    -czf $Archive .

ssh $Target "mkdir -p $RemoteDir"
scp $Archive "${Target}:$RemoteDir/app.tar.gz"
ssh $Target "cd $RemoteDir && tar -xzf app.tar.gz && rm app.tar.gz && chmod +x deploy/ubuntu_vps_bootstrap.sh && ./deploy/ubuntu_vps_bootstrap.sh"

Write-Output "Uploaded project to ${Target}:$RemoteDir"
Write-Output "If .env was just created, edit it on the server and rerun:"
Write-Output "  ssh $Target 'cd $RemoteDir && ./deploy/ubuntu_vps_bootstrap.sh'"
