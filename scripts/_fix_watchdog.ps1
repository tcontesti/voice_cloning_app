Unregister-ScheduledTask -TaskName "VCApp Tunnel Watchdog" -Confirm:$false -ErrorAction SilentlyContinue

$vbsPath = Join-Path $PSScriptRoot "tunnel_watchdog.vbs"

$action = New-ScheduledTaskAction -Execute "wscript.exe" `
    -Argument "`"$vbsPath`""

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 9999)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName "VCApp Tunnel Watchdog" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Respawn autossh tunnel to Spark (silent via VBScript wrapper)"

Write-Host "[OK] Watchdog reinstalled (wscript → no window)" -ForegroundColor Green
