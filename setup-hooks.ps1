# Enable local pre-commit hook that blocks .env, config.json, logs/, etc.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

git config core.hooksPath .githooks

Write-Host "Git hooks installed (.githooks/pre-commit)."
Write-Host "Blocked from commit: .env, config.json, logs/, __pycache__/, *.pem, *.key"
