# Build a one-line sales report from data/sales.csv.
param([string]$Path = 'data/sales.csv')

$rows = Import-Csv $Path
$total = ($rows | Measure-Object -Property amount -Sum).Sum
if (-not $total) { exit 1 }
Write-Output "total sales: $total"
