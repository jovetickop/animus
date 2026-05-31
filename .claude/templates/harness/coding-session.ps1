param(
    [string]$ProjectRoot = "."
)

$ClaudeRoot = Join-Path $ProjectRoot ".claude"
$HarnessRoot = Join-Path $ClaudeRoot "harness"
$StateRoot = Join-Path $ClaudeRoot "state"
$ShowStatus = Join-Path $HarnessRoot "show-status.py"

if (-not (Test-Path $ShowStatus)) {
    Write-Host "未在 $HarnessRoot 中找到 show-status.py"
    exit 1
}

python $ShowStatus $StateRoot
