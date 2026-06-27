# report-generator.ps1 — 报告生成模块
# 生成 Markdown 格式的任务报告，存储在 docs/reports/ 目录

function Convert-ToSafeFileName {
    param([Parameter(Mandatory = $true)][string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return "unnamed-task" }
    foreach ($invalidChar in [System.IO.Path]::GetInvalidFileNameChars()) { $Name = $Name.Replace([string]$invalidChar, "-") }
    $Name = $Name.Trim().TrimEnd(".")
    if ([string]::IsNullOrWhiteSpace($Name)) { return "unnamed-task" }
    return $Name
}

function Write-TaskReport {
    param(
        [Parameter(Mandatory = $true)][object]$Task,
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$ProgressPath,
        [Parameter(Mandatory = $true)][string]$CurrentStatus,
        [Parameter(Mandatory = $true)][string]$NewStatus,
        [Parameter(Mandatory = $true)][string]$LogMessage
    )
    $reportsDir = Join-Path $ProjectRoot "docs\reports"
    New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

    $taskId = [string]$Task.id
    $safeTaskName = Convert-ToSafeFileName -Name ([string]$Task.name)
    $reportPath = Join-Path $reportsDir ("{0}-{1}.md" -f $taskId, $safeTaskName)

    $dependsOn = @($Task.depends_on)
    $dependsOnText = if ($dependsOn.Count -gt 0) { ($dependsOn -join ", ") } else { "无" }
    $acceptanceCriteria = @()
    foreach ($criterion in @($Task.acceptance_criteria)) {
        $criterionText = [string]$criterion
        if (-not [string]::IsNullOrWhiteSpace($criterionText)) { $acceptanceCriteria += $criterionText.Trim() }
    }
    if ($acceptanceCriteria.Count -eq 0) { $acceptanceCriteria = @("未定义验收标准") }

    $testCommand = [string]$Task.test_command
    if ([string]::IsNullOrWhiteSpace($testCommand)) { $testCommand = "(未配置)" }
    $lastError = [string]$Task.last_error
    if ([string]::IsNullOrWhiteSpace($lastError)) { $lastError = "无" }

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
    if ($historyLines.Count -eq 0) { $historyLines = @("暂无任务历史记录") }

    $criteriaSection = ($acceptanceCriteria | ForEach-Object { "- $_" }) -join "`r`n"
    $historySection = ($historyLines | ForEach-Object { "- $_" }) -join "`r`n"
    $displayMessage = if ([string]::IsNullOrWhiteSpace($LogMessage)) { "(无补充说明)" } else { $LogMessage }
    $priorityValue = [string]$Task.priority
    $updatedAt = [string]$Task.updated_at

    $reportContent = @"
# $taskId - $([string]$Task.name)

## 功能描述
- 任务编号：`$taskId`
- 任务名称：$([string]$Task.name)
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
