param(
    [string]$ProjectRoot = "."
)

$ConfigPath = Join-Path $ProjectRoot ".claude\harness\project-config.json"
$FeaturesPath = Join-Path $ProjectRoot ".claude\state\features.json"

# 优先从 project-config.json 读取构建/测试命令
if (Test-Path $ConfigPath) {
    $config = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
    $buildCmd = [string]$config."build-command"
    $testCmd = [string]$config."test-command"

    if (-not [string]::IsNullOrWhiteSpace($buildCmd)) {
        Write-Host "执行构建: $buildCmd"
        Invoke-Expression $buildCmd
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "未配置构建命令，跳过构建"
    }

    if (-not [string]::IsNullOrWhiteSpace($testCmd)) {
        Write-Host "执行测试: $testCmd"
        Invoke-Expression $testCmd
        exit $LASTEXITCODE
    } else {
        Write-Host "未配置测试命令，跳过测试"
    }

    exit 0
}

# 回退：从 features.json 提取 test_command
if (Test-Path $FeaturesPath) {
    $features = Get-Content -Raw -LiteralPath $FeaturesPath | ConvertFrom-Json
    $firstTask = $features | Select-Object -First 1
    $testCmd = [string]$firstTask.test_command
    if (-not [string]::IsNullOrWhiteSpace($testCmd)) {
        Write-Host "执行测试: $testCmd"
        Invoke-Expression $testCmd
        exit $LASTEXITCODE
    }
}

Write-Host "未找到构建/测试命令，请在 project-config.json 中配置"
exit 0
