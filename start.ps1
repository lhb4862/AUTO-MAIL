Set-Location $PSScriptRoot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not installed."
    Read-Host "Press Enter to exit"
    exit 1
}
python settings_gui.py