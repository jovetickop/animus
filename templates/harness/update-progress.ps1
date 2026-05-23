param(
    [Parameter(Position = 0)]
    [string]$TaskId,
    [Parameter(Position = 1)]
    [ValidateSet("pending", "in_progress", "passed", "failed")]
    [string]$Status,
    [Parameter(Position = 2)]
    [string]$Message = "",
    [switch]$AutoPush,
    [string]$ProjectRoot = "."
)

function Ensure-TaskField {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Task,
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        $Value
    )
    if (-not $Task.PSObject.Properties[$Name]) {
        $Task | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
}

function Convert-ToSafeFileName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($Name)) {
        return "unnamed-task"
    }

    $safeName = $Name
    foreach ($invalidChar in [System.IO.Path]::GetInvalidFileNameChars()) {
        $safeName = $safeName.Replace([string]$invalidChar, "-")
    }

    $safeName = $safeName.Trim()
    $safeName = $safeName.TrimEnd(".")
    if ([string]::IsNullOrWhiteSpace($safeName)) {
        return "unnamed-task"
    }

    return $safeName
}

function Write-TaskReport {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Task,
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,
        [Parameter(Mandatory = $true)]
        [string]$ProgressPath,
        [Parameter(Mandatory = $true)]
        [string]$CurrentStatus,
        [Parameter(Mandatory = $true)]
        [string]$NewStatus,
        [Parameter(Mandatory = $true)]
        [string]$LogMessage
    )

    $reportsDir = Join-Path $ProjectRoot "docs\reports"
    New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

    $taskId = [string]$Task.id
    $taskName = [string]$Task.name
    $safeTaskName = Convert-ToSafeFileName -Name $taskName
    $reportPath = Join-Path $reportsDir ("{0}-{1}.md" -f $taskId, $safeTaskName)

    $dependsOn = @($Task.depends_on)
    $dependsOnText = if ($dependsOn.Count -gt 0) { ($dependsOn -join ", ") } else { "无" }

    $acceptanceCriteria = @()
    foreach ($criterion in @($Task.acceptance_criteria)) {
        $criterionText = [string]$criterion
        if (-not [string]::IsNullOrWhiteSpace($criterionText)) {
            $acceptanceCriteria += $criterionText.Trim()
        }
    }
    if ($acceptanceCriteria.Count -eq 0) {
        $acceptanceCriteria = @("未定义验收标准")
    }

    $testCommand = [string]$Task.test_command
    if ([string]::IsNullOrWhiteSpace($testCommand)) {
        $testCommand = "(未配置)"
    }

    $lastError = [string]$Task.last_error
    if ([string]::IsNullOrWhiteSpace($lastError)) {
        $lastError = "无"
    }

    $statusSummary = switch ($NewStatus) {
        "passed" { "验证通过" }
        "failed" { "验证失败" }
        "in_progress" { "进行中（待验证）" }
        default { "等待执行" }
    }

    $historyLines = @()
    if (Test-Path -LiteralPath $ProgressPath) {
        $taskPattern = "\|\s*$([regex]::Escape($taskId))\s*\|"
        $historyLines = @(Get-Content -LiteralPath $ProgressPath | Where-Object { $_ -match $taskPattern })
    }
    if ($historyLines.Count -eq 0) {
        $historyLines = @("暂无任务历史记录")
    }

    $criteriaSection = ($acceptanceCriteria | ForEach-Object { "- $_" }) -join "`r`n"
    $historySection = ($historyLines | ForEach-Object { "- $_" }) -join "`r`n"
    $displayMessage = if ([string]::IsNullOrWhiteSpace($LogMessage)) { "(无补充说明)" } else { $LogMessage }
    $priorityValue = [string]$Task.priority
    $updatedAt = [string]$Task.updated_at

    $reportContent = @"
# $taskId - $taskName

## 功能描述
- 任务编号：`$taskId`
- 任务名称：$taskName
- 当前状态：`$($Task.status)`
- 依赖任务：`$dependsOnText`
- 优先级：`$priorityValue`
- 验证命令：`$testCommand`

### 验收标准
$criteriaSection

## 最新验证结果
- 更新时间（UTC）：`$updatedAt`
- 本次流转：`$CurrentStatus -> $NewStatus`
- 结论：$statusSummary
- 说明：$displayMessage
- 最近失败原因：$lastError

## 过程记录（claude-progress）
$historySection
"@

    Set-Content -LiteralPath $reportPath -Encoding UTF8 -Value $reportContent
    return $reportPath
}

if ([string]::IsNullOrWhiteSpace($TaskId) -or [string]::IsNullOrWhiteSpace($Status)) {
    Write-Host "用法: .\\.claude\\harness\\update-progress.ps1 <TaskId> <Status> [Message] [-AutoPush] [-ProjectRoot .]"
    exit 1
}

$HarnessRoot = Join-Path $ProjectRoot ".claude\harness"
$FeaturesPath = Join-Path $HarnessRoot "features.json"
$ProgressPath = Join-Path $HarnessRoot "claude-progress.txt"

if (-not (Test-Path $FeaturesPath)) {
    Write-Host "未在 $HarnessRoot 中找到 features.json"
    exit 1
}

$features = Get-Content -Raw -LiteralPath $FeaturesPath | ConvertFrom-Json

foreach ($task in @($features)) {
    Ensure-TaskField -Task $task -Name "depends_on" -Value @()
    Ensure-TaskField -Task $task -Name "priority" -Value 0
    Ensure-TaskField -Task $task -Name "last_error" -Value ""
    Ensure-TaskField -Task $task -Name "updated_at" -Value ""

    $deps = @()
    foreach ($dep in @($task.depends_on)) {
        $depId = [string]$dep
        if (-not [string]::IsNullOrWhiteSpace($depId)) {
            $deps += $depId.Trim()
        }
    }
    $task.depends_on = $deps

    try {
        $task.priority = [int]$task.priority
    }
    catch {
        $task.priority = 0
    }
}

$targetTask = $features | Where-Object { $_.id -eq $TaskId } | Select-Object -First 1
if (-not $targetTask) {
    Write-Host "未找到任务 $TaskId"
    exit 1
}

$taskById = @{}
foreach ($task in @($features)) {
    $taskById[[string]$task.id] = $task
}

$currentStatus = [string]$targetTask.status

switch ($Status) {
    "in_progress" {
        if ($currentStatus -notin @("pending", "failed", "in_progress")) {
            Write-Host "非法状态流转: $TaskId 不允许从 $currentStatus 变为 in_progress"
            exit 1
        }

        if ($currentStatus -ne "in_progress") {
            $otherInProgress = @($features | Where-Object { $_.id -ne $TaskId -and $_.status -eq "in_progress" })
            if ($otherInProgress.Count -gt 0) {
                $otherIds = ($otherInProgress | ForEach-Object { $_.id }) -join ", "
                Write-Host "状态冲突: 已存在进行中任务 ($otherIds)。请先处理完成或回退后再切换 $TaskId。"
                exit 1
            }

            $missingDeps = @()
            $unmetDeps = @()
            foreach ($depId in @($targetTask.depends_on)) {
                if (-not $taskById.ContainsKey($depId)) {
                    $missingDeps += $depId
                    continue
                }

                if ([string]$taskById[$depId].status -ne "passed") {
                    $unmetDeps += $depId
                }
            }

            if ($missingDeps.Count -gt 0) {
                Write-Host ("依赖配置错误: 任务 {0} 引用了不存在的 depends_on: {1}" -f $TaskId, ($missingDeps -join ", "))
                exit 1
            }

            if ($unmetDeps.Count -gt 0) {
                Write-Host ("依赖未满足: 任务 {0} 仍需等待 {1} 先通过" -f $TaskId, ($unmetDeps -join ", "))
                exit 1
            }
        }
    }
    "passed" {
        if ($currentStatus -ne "in_progress") {
            Write-Host "非法状态流转: $TaskId 只能从 in_progress 变为 passed"
            exit 1
        }
    }
    "failed" {
        if ($currentStatus -ne "in_progress") {
            Write-Host "非法状态流转: $TaskId 只能从 in_progress 变为 failed"
            exit 1
        }
    }
    "pending" {
        if ($currentStatus -notin @("failed", "in_progress", "pending")) {
            Write-Host "非法状态流转: $TaskId 不允许从 $currentStatus 变为 pending"
            exit 1
        }
    }
}

$logMessage = $Message
if ($Status -eq "failed" -and [string]::IsNullOrWhiteSpace($logMessage)) {
    $logMessage = "未提供失败原因"
}

$targetTask.status = $Status
$targetTask.updated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
if ($Status -eq "failed") {
    $targetTask.last_error = $logMessage
}
else {
    $targetTask.last_error = ""
}

$features | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $FeaturesPath -Encoding UTF8

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -LiteralPath $ProgressPath -Value "$timestamp | $TaskId | $currentStatus -> $Status | $logMessage"

$reportPath = Write-TaskReport `
    -Task $targetTask `
    -ProjectRoot $ProjectRoot `
    -ProgressPath $ProgressPath `
    -CurrentStatus $currentStatus `
    -NewStatus $Status `
    -LogMessage $logMessage

Write-Host "已将 $TaskId 从 $currentStatus 更新为 $Status"
Write-Host "已输出任务报告: $reportPath"

if ($AutoPush) {
    git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "当前目录不是 Git 仓库，跳过 AutoPush"
        exit 0
    }

    git add -- $FeaturesPath $ProgressPath $reportPath
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "没有可提交的变更，跳过 AutoPush"
        exit 0
    }

    $commitMessage = "chore(harness): update $TaskId to $Status"
    git commit -m $commitMessage
    if ($LASTEXITCODE -ne 0) {
        Write-Host "AutoPush: git commit 失败，请人工处理。"
        exit 1
    }

    git push
    if ($LASTEXITCODE -ne 0) {
        Write-Host "AutoPush: git push 失败，请人工处理。"
        exit 1
    }
}
