param(
    [string]$ProjectRoot = "."
)

# ===== 路径定义 =====
$ClaudeRoot = Join-Path $ProjectRoot ".claude"
$HarnessRoot = Join-Path $ClaudeRoot "harness"
$StateRoot = Join-Path $ClaudeRoot "state"
$FeaturesFile = Join-Path $StateRoot "features.json"
$ShowStatus = Join-Path $HarnessRoot "show-status.py"

# ===== 1. 运行原有的状态展示脚本 =====
if (-not (Test-Path $ShowStatus)) {
    Write-Host "错误: 在 $HarnessRoot 未找到 show-status.py"
    exit 1
}

python $ShowStatus $StateRoot

# 输出分隔行，与新增内容区分
Write-Host ""
Write-Host ("=" * 50) -ForegroundColor Cyan
Write-Host "【任务状态概览】" -ForegroundColor Cyan
Write-Host ("=" * 50) -ForegroundColor Cyan

# ===== 2. 读取 features.json，检查任务状态 =====
if (-not (Test-Path $FeaturesFile)) {
    Write-Host "提示: 未找到 $FeaturesFile，跳过任务状态检查" -ForegroundColor Yellow
    exit 0
}

try {
    # 读取 features.json 并解析为 PowerShell 对象
    $FeaturesContent = Get-Content $FeaturesFile -Raw -Encoding UTF8
    $Features = $FeaturesContent | ConvertFrom-Json
} catch {
    Write-Host "警告: 解析 $FeaturesFile 失败: $_" -ForegroundColor Yellow
    exit 0
}

# ===== 3. 统计各状态的任务数量 =====
$Tasks = $Features.tasks
if ($null -eq $Tasks -or $Tasks.Count -eq 0) {
    Write-Host "提示: features.json 中没有定义任何任务" -ForegroundColor Yellow
    exit 0
}

# 按状态分组统计
$TotalCount = $Tasks.Count
$PassedCount = ($Tasks | Where-Object { $_.status -eq "passed" }).Count
$PendingCount = ($Tasks | Where-Object { $_.status -eq "pending" }).Count
$FailedCount = ($Tasks | Where-Object { $_.status -eq "failed" }).Count
$InProgressCount = ($Tasks | Where-Object { $_.status -eq "in_progress" }).Count

# 输出统计信息
Write-Host "总计: $TotalCount 个任务"
Write-Host "  [通过] passed  : $PassedCount" -ForegroundColor Green
Write-Host "  [进行] in_progress: $InProgressCount" -ForegroundColor Yellow
Write-Host "  [待办] pending : $PendingCount" -ForegroundColor Gray
Write-Host "  [失败] failed  : $FailedCount" -ForegroundColor Red

# ===== 4. 检查是否有进行中的任务，输出恢复建议 =====
if ($InProgressCount -gt 0) {
    Write-Host ""
    Write-Host ("-" * 40) -ForegroundColor Cyan
    Write-Host "【进行中的任务 - 可恢复】" -ForegroundColor Yellow

    # 遍历所有 in_progress 任务，打印 ID 和名称
    $InProgressTasks = $Tasks | Where-Object { $_.status -eq "in_progress" }
    foreach ($Task in $InProgressTasks) {
        $TaskId = $Task.id
        $TaskName = $Task.name
        Write-Host "  - $TaskId : $TaskName"
    }

    # 生成恢复建议（默认取第一个 in_progress 任务）
    Write-Host ""
    Write-Host "【恢复建议】" -ForegroundColor Cyan
    foreach ($Task in $InProgressTasks) {
        Write-Host "  继续 $($Task.id) ($($Task.name))" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "没有进行中的任务。可以使用 '开始新任务' 启动一个新的开发周期。" -ForegroundColor Green
}
