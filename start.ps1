Set-Location $PSScriptRoot

$pythonw = Get-Command pythonw -ErrorAction SilentlyContinue
if (-not $pythonw) {
    $pythonw = Get-Command pyw -ErrorAction SilentlyContinue
    if ($pythonw) {
        Start-Process pyw -ArgumentList "-3", "settings_gui.py" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
        exit 0
    }
    Write-Host "Python is not installed."
    Read-Host "Press Enter to exit"
    exit 1
}

Start-Process pythonw -ArgumentList "settings_gui.py" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
