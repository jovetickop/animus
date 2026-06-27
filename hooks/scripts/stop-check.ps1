# Stop 钩子 — 会话结束时检查未完成任务的状态
# 解析 features.json，输出中文警告提醒用户有未完成的任务
# 始终以 exit 0 退出

# 确定项目根目录（优先使用环境变量，否则从脚本路径推导）
$projectRoot = if ($env:CLAUDE_PROJECT_ROOT) {
    $env:CLAUDE_PROJECT_ROOT
} elseif ($env:CLAUDE_PLUGIN_ROOT) {
    $env:CLAUDE_PLUGIN_ROOT
} else {
    # 从脚本路径 .claude/hooks/scripts/ 向上三级到项目根
    Resolve-Path "$PSScriptRoot/../../.."
}

$featuresPath = Join-Path $projectRoot ".claude" "state" "features.json"

# 检查 features.json 是否存在
if (-not (Test-Path -LiteralPath $featuresPath)) {
    exit 0
}

# 解析 features.json 获取任务列表
try {
    $features = Get-Content -Raw -LiteralPath $featuresPath -Encoding UTF8 | ConvertFrom-Json
} catch {
    # JSON 解析失败时静默退出
    exit 0
}

# 获取任务数组（兼容数组格式和对象格式如 {initial_tasks}/tasks）
$tasks = @()
if ($features -is [Array]) {
    $tasks = $features
} elseif ($features -is [PSCustomObject]) {
    if ($features.initial_tasks) { $tasks = @($features.initial_tasks) }
    elseif ($features.tasks) { $tasks = @($features.tasks) }
}

# 查找所有状态为 in_progress 的未完成任务
$inProgressTasks = $tasks | Where-Object { $_.status -eq "in_progress" }

if ($inProgressTasks.Count -gt 0) {
    Write-Host "===== 任务状态检查 ====="
    Write-Host "以下任务正在进行中，尚未完成："
    foreach ($task in $inProgressTasks) {
        $taskId = [string]$task.id
        $taskName = [string]$task.name
        if ([string]::IsNullOrWhiteSpace($taskName)) { $taskName = "(未命名)" }
        Write-Host "  - $taskId : $taskName"
    }
    Write-Host "请确认这些任务是否需要继续或回退状态。"
}

exit 0
