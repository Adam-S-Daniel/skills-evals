#!/usr/bin/env bash
# List Windows drives that hold data, from WSL.
set -euo pipefail

powershell.exe -NoProfile -Command "Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 } | ForEach-Object { '{0} {1}' -f $_.Name, $_.Used }"
