param(
    [string]$Source = 'D:\Team Share\Weekly Reports',
    [string]$Dest = 'D:\outbox\reports'
)

Copy-Item -Path $Source -Destination $Dest -Recurse
