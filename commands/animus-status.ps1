param(
    [string]$Arg = ""
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

# === 1. 确定状态目录路径 ===
$StateDir = Join-Path (Join-Path $PWD ".claude") "animus"
$featuresPath = Join-Path $StateDir "features.json"

# === 2. 检查 features.json 是否存在 ===
if (-not (Test-Path $featuresPath)) {
    Write-Host "[animus] 错误: 未找到 .claude/animus/features.json"
    Write-Host "[animus] 请先在目标项目中运行 /animus-setup 初始化工作目录"
    exit 1
}

# === 3. 调用 Python 状态展示脚本 ===
$scriptPath = $PSScriptRoot
$scriptPath = Join-Path $scriptPath ".."
$scriptPath = Join-Path $scriptPath "templates"
$scriptPath = Join-Path $scriptPath "animus"
$scriptPath = Join-Path $scriptPath "show-status.py"
$pythonCmd = "python"

# 解析 Python 命令（兼容 python / python3）
try {
    $null = Get-Command "python" -ErrorAction Stop
} catch {
    try {
        $null = Get-Command "python3" -ErrorAction Stop
        $pythonCmd = "python3"
    } catch {
        Write-Host "[animus] 错误: 未找到 python 或 python3，请安装 Python"
        exit 1
    }
}

# === 4. 执行 Python 脚本 ===
try {
    if ($Arg -ne "") {
        Write-Progress -Activity "animus Status" -Status "Running status script" -PercentComplete 50
        & $pythonCmd $scriptPath $StateDir $Arg 2>&1 | ForEach-Object { Write-Host $_ }
    } else {
        Write-Progress -Activity "animus Status" -Status "Running status script" -PercentComplete 50
        & $pythonCmd $scriptPath $StateDir 2>&1 | ForEach-Object { Write-Host $_ }
    }
} catch {
    Write-Host "[animus] 警告: 状态脚本执行失败: $_"
    Write-Host "[animus] 这将不会阻塞后续操作"
}

# === 5. 完成 ===
Write-Progress -Activity "animus Status" -Status "Done" -PercentComplete 100

$elapsed = [DateTime](Get-Date) - [DateTime]$startTime
$elapsedStr = $elapsed.TotalSeconds.ToString('0.0')
Write-Host ""
Write-Host "[animus] 状态查询完成，耗时 ${elapsedStr}s"
