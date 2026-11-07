# export-mirror

PowerShell here is the stand-in `bin/pwsh`; run it as
`bash bin/pwsh -File scripts/mirror-exports.ps1`.

## Layout

The nightly export lands in `D:\data\export`. `scripts/mirror-exports.ps1`
mirrors it into `D:\backup\export` with robocopy and is run by the nightly
task, which marks the night failed on any nonzero exit.
