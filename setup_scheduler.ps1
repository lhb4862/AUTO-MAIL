# Register AUTO-MAIL tasks in Windows Task Scheduler.
# Run in PowerShell: .\setup_scheduler.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonExe = "py"
    } else {
        throw "Python not found. Add python or py to PATH."
    }
}

$MainScript = Join-Path $ProjectRoot "main.py"
$ConfigPath = Join-Path $ProjectRoot "config.json"
$TaskPrefix = "AUTO-MAIL"

if (-not (Test-Path $ConfigPath)) {
    throw "config.json not found: $ConfigPath"
}

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$times = @($config.schedule.times)

if ($times.Count -eq 0) {
    throw "schedule.times is empty in config.json"
}

$actionArgs = if ($PythonExe -eq "py") {
    "-3 `"$MainScript`" --skip-schedule"
} else {
    "`"$MainScript`" --skip-schedule"
}

$action = New-ScheduledTaskAction -Execute $PythonExe -Argument $actionArgs -WorkingDirectory $ProjectRoot

Get-ScheduledTask -TaskName "$TaskPrefix-*" -ErrorAction SilentlyContinue | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
}

foreach ($time in $times) {
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $time
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $taskName = "$TaskPrefix-$time"
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "AUTO-MAIL weekday send at $time"
    Write-Host "Registered: $taskName (weekdays at $time)"
}

Write-Host ""
Write-Host "Note: default SEND_EMAIL=False. Set SEND_EMAIL=True in .env before live sends."