param(
    [string]$Source = 'D:\data\exports',
    [string]$Dest = 'D:\backup\export'
)

Copy-Item -Path $Source -Destination $Dest -Recurse
