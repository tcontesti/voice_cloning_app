Set objShell = CreateObject("WScript.Shell")
objShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -NonInteractive -File """ & Replace(WScript.ScriptFullName, "tunnel_watchdog.vbs", "tunnel_watchdog.ps1") & """", 0, False
