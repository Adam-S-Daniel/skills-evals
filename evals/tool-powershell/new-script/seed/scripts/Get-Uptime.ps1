# Get-Uptime.ps1 - print how long this machine has been up.
# Run: pwsh -NoProfile -File scripts/Get-Uptime.ps1
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'

$boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
Write-Output ("up {0:N1} hours" -f ((Get-Date) - $boot).TotalHours)
exit 0
