<#
.SYNOPSIS
    验证 features.json 是否遵循 append-only 模式（禁止删除已有任务）
.DESCRIPTION
    从 harness-history.jsonl 中提取所有历史 task_id，与 features.json 当前任务对比。
    如果历史中出现过的 task_id 当前不存在，则报告 append-only 违规。
.PARAMETER StateDir
    .claude/harness-cc 目录路径，默认为 ".claude/harness-cc"
.EXAMPLE
    powershell -File validate-append-only.ps1 -StateDir ".claude/harness-cc"
#>
param(
    [string]$StateDir = ".claude/harness-cc"
)

$ErrorActionPreference = "Stop"

$featuresPath = Join-Path $StateDir "features.json"
$historyPath = Join-Path $StateDir "harness-history.jsonl"

# 检查 features.json 是否存在
if (-not (Test-Path $featuresPath)) {
    Write-Host "SKIP: features.json not found at $featuresPath"
    exit 0
}

# 读取 features.json
try {
    $data = Get-Content $featuresPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Host "FAILED: Cannot parse features.json: $_"
    exit 1
}

$tasks = if ($data -isnot [array]) { @($data.tasks) } else { $data }
$currentIds = @{}
foreach ($task in $tasks) {
    $currentIds[[string]$task.id] = $true
}

# 从 JSONL 提取历史 task_id
$historicalIds = @{}
if (Test-Path $historyPath) {
    $lines = Get-Content $historyPath -Encoding UTF8
    $lineNum = 0
    foreach ($line in $lines) {
        $lineNum++
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $parsed = $line | ConvertFrom-Json
            if ($parsed.task_id) {
                $historicalIds[[string]$parsed.task_id] = $true
            }
        } catch {
            Write-Host "WARN: JSONL line $lineNum 解析失败 (跳过)"
        }
    }
}

# Append-only 检查
$violations = @()
foreach ($histId in $historicalIds.Keys) {
    if (-not $currentIds.ContainsKey($histId)) {
        $violations += $histId
    }
}

if ($violations.Count -gt 0) {
    $ids = $violations -join ", "
    Write-Host "FAILED: Append-only 违规！以下任务曾在 JSONL 历史中出现但已被删除: $ids"
    Write-Host "建议: 从备份文件 features.json.bak.* 恢复，或通过 update-progress.ps1 重新添加"
    exit 1
} else {
    Write-Host "PASSED: Append-only check OK ($($currentIds.Count) tasks, $($historicalIds.Count) historical)"
    exit 0
}
