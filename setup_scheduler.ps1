# Register AUTO-MAIL tasks in Windows Task Scheduler.
# Run in PowerShell: .\setup_scheduler.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$UsePyLauncher = $false
$PythonExe = $null

$cmd = Get-Command pythonw -ErrorAction SilentlyContinue
if ($cmd) {
    $PythonExe = $cmd.Source
}
if (-not $PythonExe -and (Get-Command pyw -ErrorAction SilentlyContinue)) {
    $PythonExe = "pyw"
    $UsePyLauncher = $true
}
if (-not $PythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $PythonExe = $cmd.Source
    }
}
if (-not $PythonExe -and (Get-Command py -ErrorAction SilentlyContinue)) {
    $PythonExe = "py"
    $UsePyLauncher = $true
}
if (-not $PythonExe) {
    throw "Python not found. Add pythonw or pyw to PATH."
}

$MainScript = Join-Path $ProjectRoot "main.py"
$ConfigPath = Join-Path $ProjectRoot "config.json"
$TaskPrefix = "AUTO-MAIL"

if (-not (Test-Path $ConfigPath)) {
    throw "config.json not found: $ConfigPath"
}

$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$times = @($config.schedule.times)

Get-ScheduledTask -TaskName "$TaskPrefix-*" -ErrorAction SilentlyContinue | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
}

if ($times.Count -eq 0) {
    Write-Host "No send times configured. Removed existing AUTO-MAIL tasks."
    Write-Host ""
    Write-Host "Done."
    exit 0
}

$dayMap = @{
    mon = "Monday"
    tue = "Tuesday"
    wed = "Wednesday"
    thu = "Thursday"
    fri = "Friday"
    sat = "Saturday"
    sun = "Sunday"
}

$selectedDays = @($config.schedule.days)
if ($selectedDays.Count -eq 0) {
    if ($config.schedule.weekdays_only -eq $false) {
        $selectedDays = @("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    } else {
        $selectedDays = @("mon", "tue", "wed", "thu", "fri")
    }
}

$weekDays = @()
foreach ($day in $selectedDays) {
    if ($dayMap.ContainsKey($day)) {
        $weekDays += $dayMap[$day]
    }
}

if ($weekDays.Count -eq 0) {
    throw "schedule.days is empty in config.json"
}

$actionArgs = if ($UsePyLauncher) {
    "-3 `"$MainScript`" --skip-schedule"
} else {
    "`"$MainScript`" --skip-schedule"
}

$action = New-ScheduledTaskAction -Execute $PythonExe -Argument $actionArgs -WorkingDirectory $ProjectRoot

foreach ($time in $times) {
    $safeTime = $time -replace ":", "-"
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $weekDays -At $time
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $taskName = "$TaskPrefix-$safeTime"
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "AUTO-MAIL send at $time on selected weekdays"
    Write-Host "Registered: $taskName ($($weekDays -join ', ') at $time)"
}

Write-Host ""
Write-Host "Done. SEND_EMAIL=True in .env is required for live sends."
