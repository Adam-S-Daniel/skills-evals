# wsl-backup

Nightly export of every WSL distro on this machine (`ZENDA`) to
`D:\Backups\wsl`, driven by a Windows scheduled task.

This checkout lives at `D:\repos\adam-s-daniel\wsl-backup` and is worked on
from **inside WSL** (`/mnt/d/repos/adam-s-daniel/wsl-backup`). Windows
PowerShell is reachable from the WSL shell as `powershell.exe` (Windows
PowerShell 5.1) or `pwsh.exe` (PowerShell 7); both are on `PATH`.

## Layout

| Path | What |
| --- | --- |
| `scripts/backup.ps1` | the export itself (`wsl --export` per distro, then rotation) |
| `scripts/register-tasks.ps1` | registers (or re-registers) the `\WslAutomation\WSL-Backup` task |

## The task

`\WslAutomation\WSL-Backup` runs `scripts/backup.ps1` as the owning user
(`$env:USERDOMAIN\$env:USERNAME`, S4U logon so no stored password) at
`RunLevel Highest`, because `wsl --export` needs the elevated token to read
every distro's vhdx. It is registered with `-Force`, so re-running
`register-tasks.ps1` replaces the existing task in place — that is how a
trigger or setting change is applied.

Inspect it with `Get-ScheduledTask -TaskPath '\WslAutomation\'` and
`Get-ScheduledTaskInfo`; `Export-ScheduledTask` prints the full XML.
