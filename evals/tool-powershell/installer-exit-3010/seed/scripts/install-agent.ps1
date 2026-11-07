param(
    [string]$Package = 'D:\packages\agent.msi'
)

msiexec /i $Package /qn /norestart
