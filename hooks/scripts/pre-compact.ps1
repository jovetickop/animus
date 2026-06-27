# PreCompact 钩子 — 上下文压缩前刷新进度到 claude-progress.txt
# 追加时间戳 [COMPACT] 标记行，并输出 features.json 任务完成摘要
# 始终以 exit 0 退出，不影响压缩流程

# 确定项目根目录（优先使用环境变量，否则从脚本路径推导）
$projectRoot = if ($env:CLAUDE_PROJECT_ROOT) {
    $env:CLAUDE_PROJECT_ROOT
} elseif ($env:CLAUDE_PLUGIN_ROOT) {
    $env:CLAUDE_PLUGIN_ROOT
} else {
    # 从脚本路径 .claude/hooks/scripts/ 向上三级到项目根
    Resolve-Path "$PSScriptRoot/../../.."
}

# 统一路径查找：features.json 固定在 .claude/state/
$featuresPath = Join-Path $projectRoot ".claude" "state" "features.json"

# 旧路径 deprecated 警告（仅提示，不影响逻辑）
$oldFeaturesPath = Join-Path $projectRoot ".claude" "harness" "features.json"
if (Test-Path -LiteralPath $oldFeaturesPath) {
    Write-Host "[harness-cc] WARNING: features.json 在旧路径 .claude/harness/ (deprecated). 请迁移到 .claude/state/" -ForegroundColor Yellow
}

$progressPath = Join-Path $projectRoot ".claude" "state" "claude-progress.txt"

# 1) 如果 claude-progress.txt 存在，追加时间戳 [COMPACT] 标记行
if (Test-Path -LiteralPath $progressPath) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $marker = "[COMPACT] 上下文压缩于 $timestamp"
    Add-Content -LiteralPath $progressPath -Value $marker -Encoding UTF8
}

# 2) 如果 features.json 存在，统计任务完成情况并输出摘要
if (Test-Path -LiteralPath $featuresPath) {
    try {
        $features = Get-Content -Raw -LiteralPath $featuresPath -Encoding UTF8 | ConvertFrom-Json

        # 兼容数组格式和对象格式（initial_tasks/tasks 字段）
        $tasks = @()
        if ($features -is [Array]) {
            $tasks = $features
        } elseif ($features -is [PSCustomObject]) {
            if ($features.initial_tasks) { $tasks = @($features.initial_tasks) }
            elseif ($features.tasks) { $tasks = @($features.tasks) }
        }

        $totalCount = $tasks.Count
        if ($totalCount -gt 0) {
            # 统计状态为 passed 或 completed 的已完成任务数
            $doneCount = ($tasks | Where-Object { $_.status -in @("passed", "completed") }).Count
            Write-Host "[harness-cc] PreCompact: $doneCount/$totalCount 任务完成"
        }
    } catch {
        # features.json 解析失败时静默处理，不影响压缩流程
    }
}

exit 0
