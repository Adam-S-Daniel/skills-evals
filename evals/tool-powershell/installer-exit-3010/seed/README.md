# agent-installer

PowerShell here is the stand-in `bin/pwsh`; run it as
`bash bin/pwsh -File scripts/install-agent.ps1`.

`scripts/install-agent.ps1` installs the monitoring agent with msiexec and is
run by the rollout task, which marks a machine failed on any nonzero exit.
The package installs fine on every machine; do not change the msiexec line.
