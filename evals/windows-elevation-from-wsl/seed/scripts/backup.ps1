# Export every registered WSL distro to D:\Backups\wsl and keep the last 7.
$ErrorActionPreference = "Stop"
$dest = "D:\Backups\wsl"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
foreach ($distro in (wsl.exe --list --quiet | Where-Object { $_ })) {
    $name = $distro.Trim()
    wsl.exe --export $name (Join-Path $dest "$name-$stamp.tar")
}
Get-ChildItem $dest -Filter "*.tar" | Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 7 | Remove-Item
