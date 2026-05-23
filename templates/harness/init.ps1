param(
    [string]$ProjectRoot = "."
)

$HarnessRoot = Join-Path $ProjectRoot ".claude\harness"
$BuildDir = Join-Path $ProjectRoot "build"

New-Item -ItemType Directory -Force -Path $HarnessRoot | Out-Null

if (-not (Test-Path (Join-Path $HarnessRoot "features.json"))) {
    Write-Host "未在 $HarnessRoot 中找到 features.json"
    exit 1
}

if (-not (Test-Path $BuildDir)) {
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
}

Write-Host "已初始化 harness：$HarnessRoot"
