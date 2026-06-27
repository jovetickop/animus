param(
    [string]$ProjectRoot = "."
)

$ClaudeRoot = Join-Path $ProjectRoot ".claude"
$StateRoot = Join-Path $ClaudeRoot "state"
$HarnessRoot = Join-Path $ClaudeRoot "harness"
$BuildDir = Join-Path $ProjectRoot "build"

New-Item -ItemType Directory -Force -Path $StateRoot | Out-Null
New-Item -ItemType Directory -Force -Path $HarnessRoot | Out-Null

if (-not (Test-Path (Join-Path $StateRoot "features.json"))) {
    Write-Host "未在 $StateRoot 中找到 features.json"
    exit 1
}

if (-not (Test-Path $BuildDir)) {
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
}

Write-Host "已初始化 harness：$HarnessRoot"

