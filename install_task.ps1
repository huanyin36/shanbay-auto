param(
    [string]$TaskName = 'ShanbayDaily'
)
$ErrorActionPreference = 'Stop'

# run.bat lives next to this script; resolve from PSScriptRoot so paths with spaces work.
$runBat = Join-Path $PSScriptRoot 'run.bat'

$action   = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "{0}"' -f $runBat)
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Output ('[OK] Task "{0}" registered -> runs {1} at logon.' -f $TaskName, $runBat)
