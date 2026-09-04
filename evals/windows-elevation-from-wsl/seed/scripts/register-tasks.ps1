<#
.SYNOPSIS
  Register (or re-register) the \WslAutomation\WSL-Backup scheduled task.

.PARAMETER BackupTime
  Daily trigger time, HH:mm (24h). Default 02:00.
#>
[CmdletBinding()]
param(
    [string]$BackupTime = "02:00"
)

$ErrorActionPreference = "Stop"

$taskPath = "\WslAutomation\"
$taskName = "WSL-Backup"
$scriptPath = Join-Path $PSScriptRoot "backup.ps1"

$action = New-ScheduledTaskAction -Execute "pwsh.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -Daily -At $BackupTime

# The owning user, never SYSTEM: WSL distros are registered per Windows user,
# and a SYSTEM task sees none of them. S4U so no password is stored.
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskPath $taskPath -TaskName $taskName `
    -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description "Nightly export of every WSL distro to D:\Backups\wsl." `
    -Force | Out-Null

Write-Host "Registered $taskPath$taskName (daily at $BackupTime)."
