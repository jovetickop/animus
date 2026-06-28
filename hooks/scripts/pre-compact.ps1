# PreCompact 钩子 — 上下文压缩前刷新进度到 claude-progress.txt
# 追加时间戳 [COMPACT] 标记行，并输出 features.json 任务完成摘要
# 始终以 exit 0 退出，不影响压缩流程

# 确定项目根目录（优先使用环境变量，否则从脚本路径推导）
$projectRoot = if ($env:CLAUDE_PROJECT_ROOT) {
    $env:CLAUDE_PROJECT_ROOT
} else {
    # 从脚本路径 .claude/hooks/scripts/ 向上三级到项目根
    Resolve-Path "$PSScriptRoot/../../.."
}

# 统一路径查找：features.json 固定在 .claude/harness-cc/
$featuresPath = Join-Path $projectRoot ".claude" "harness-cc" "features.json"

# 旧路径 deprecated 警告（同时检查 .claude/state/ 和 .claude/harness/）
$oldStatePath = Join-Path $projectRoot ".claude" "state" "features.json"
$oldHarnessPath = Join-Path $projectRoot ".claude" "harness" "features.json"
if (Test-Path -LiteralPath $oldStatePath) {
    Write-Host "[harness-cc] WARNING: features.json 在旧路径 .claude/state/ (deprecated). 请迁移到 .claude/harness-cc/" -ForegroundColor Yellow
}
if (Test-Path -LiteralPath $oldHarnessPath) {
    Write-Host "[harness-cc] WARNING: features.json 在旧路径 .claude/harness/ (deprecated). 请迁移到 .claude/harness-cc/" -ForegroundColor Yellow
}

$progressPath = Join-Path $projectRoot ".claude" "harness-cc" "claude-progress.txt"
$historyPath = Join-Path $projectRoot ".claude" "harness-cc" "harness-history.jsonl"

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

            # 3) 写入 JSONL compact 事件
            if (Test-Path -LiteralPath $historyPath) {
                try {
                    $compactRecord = @{
                        type = "compact"
                        timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
                        reason = "context_window_reached"
                        summary = "$doneCount/$totalCount 任务完成"
                    }
                    "---" | Add-Content -LiteralPath $historyPath -Encoding UTF8
                    $compactRecord | ConvertTo-Json -Depth 3 | Add-Content -LiteralPath $historyPath -Encoding UTF8
                } catch { }
            }

            # 4) 自动同步 features.json → task_plan.md
            $taskPlanPath = Join-Path $projectRoot ".claude" "harness-cc" "task_plan.md"
            if (Test-Path -LiteralPath $taskPlanPath) {
                try {
                    $planContent = Get-Content -LiteralPath $taskPlanPath -Encoding UTF8
                    $modified = $false
                    foreach ($task in $tasks) {
                        if ($task.status -eq "passed" -or $task.status -eq "completed") {
                            $taskId = [string]$task.id
                            # 查找 [ ] Txxx 样式的 checkbox 并标记为 [x]
                            $pattern = "\[ \] ([^\]]*${taskId}[^\]]*)"
                            $newContent = $planContent -replace $pattern, '[x] $1'
                            if ($newContent -ne $planContent) {
                                $planContent = $newContent
                                $modified = $true
                            }
                        }
                    }
                    if ($modified) {
                        $planContent | Set-Content -LiteralPath $taskPlanPath -Encoding UTF8
                        # 记录 sync 事件
                        $syncRecord = @{
                            type = "sync"
                            timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
                            action = "task_plan_checkbox_auto_synced"
                        }
                        "---" | Add-Content -LiteralPath $historyPath -Encoding UTF8
                        $syncRecord | ConvertTo-Json -Depth 3 | Add-Content -LiteralPath $historyPath -Encoding UTF8
                    }
                } catch { }
            }
        }
    } catch {
        # features.json 解析失败时静默处理，不影响压缩流程
    }

    # 5) Append-only 检测：从 JSONL 提取历史 task_id，检查是否被删除
    if (Test-Path -LiteralPath $historyPath) {
        try {
            $historyContent = Get-Content -LiteralPath $historyPath -Raw -Encoding UTF8
            $historyBlocks = $historyContent -split '---\r?\n'
            $historicalIds = @{}
            foreach ($hBlock in $historyBlocks) {
                $hTrimmed = $hBlock.Trim()
                if (-not $hTrimmed) { continue }
                try { $hParsed = $hTrimmed | ConvertFrom-Json; if ($hParsed.task_id) { $historicalIds[[string]$hParsed.task_id] = $true } } catch {}
            }
            $currentIds = @{}
            foreach ($t in $tasks) { $currentIds[[string]$t.id] = $true }
            $missingIds = @()
            foreach ($hId in $historicalIds.Keys) {
                if (-not $currentIds.ContainsKey($hId)) { $missingIds += $hId }
            }
            if ($missingIds.Count -gt 0) {
                Write-Host "[harness-cc] WARNING: Append-only 违规！以下任务已从 features.json 中删除: $($missingIds -join ', ')" -ForegroundColor Red
                Write-Host "[harness-cc] 建议从备份 features.json.bak.* 中恢复" -ForegroundColor Yellow
            }
        } catch { }
    }

}

exit 0
