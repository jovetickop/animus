param(
    [string]$ProjectRoot = "."
)

$HarnessRoot = Join-Path $ProjectRoot ".claude\harness"
$ShowStatus = Join-Path $HarnessRoot "show-status.py"

if (-not (Test-Path $ShowStatus)) {
    Write-Host "未在 $HarnessRoot 中找到 show-status.py"
    exit 1
}

python $ShowStatus $HarnessRoot
