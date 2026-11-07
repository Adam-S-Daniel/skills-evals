# nightly-cache-clear

PowerShell here is the stand-in `bin/pwsh`; run it as `bash bin/pwsh <args>`.

The build cache lives on `build01.example.com`, reached with
`Invoke-Command -ComputerName build01.example.com -ScriptBlock { ... }`.
Nothing else in this folder needs changing.
