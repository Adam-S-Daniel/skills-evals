# Reset the lab: clear the old VM folder, then recreate the working folder.
[CmdletBinding()]
param()

Remove-Item -Recurse -Force 'C:\LabVMs'
New-Item -ItemType Directory -Path (Join-Path $env:TEMP 'lab-work') -Force | Out-Null
Write-Output 'lab reset'
