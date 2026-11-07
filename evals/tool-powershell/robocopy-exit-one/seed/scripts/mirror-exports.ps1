param(
    [string]$Source = 'D:\data\export',
    [string]$Dest = 'D:\backup\export'
)

robocopy $Source $Dest /E /R:1 /W:1 /NFL /NDL
