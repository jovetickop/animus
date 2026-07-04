param(
    [string]$StateDir = ".claude/animus"
)

$ErrorActionPreference = "Stop"
$warnings = @()

$featuresPath = Join-Path $StateDir "features.json"
$historyPath = Join-Path $StateDir "animus-history.jsonl"

if (-not (Test-Path $featuresPath)) {
    Write-Host "FAILED: features.json not found: $featuresPath"
    exit 1
}

# Read features.json
try {
    $data = Get-Content $featuresPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Host "FAILED: Cannot parse features.json: $_"
    exit 1
}

$taskStatus = @{}
if ($data -isnot [array]) {
    if ($data.PSObject.Properties['initial_tasks']) { $data = $data.initial_tasks }
    elseif ($data.PSObject.Properties['tasks']) { $data = $data.tasks }
}
foreach ($task in $data) {
    $taskStatus[$task.id] = @{
        status = $task.status
        updated_at = if ($task.updated_at) { $task.updated_at } else { "" }
    }
}

# JSONL 校验：检测损坏行 + append-only 检查
$jsonlErrors = @()
$knownTaskIds = @{}
if (Test-Path $historyPath) {
    $content = Get-Content $historyPath -Raw -Encoding UTF8
    $blocks = $content -split '---\r?\n'
    $blockNum = 0
    foreach ($block in $blocks) {
        $blockNum++
        $trimmed = $block.Trim()
        if (-not $trimmed) { continue }
        try {
            $parsed = $trimmed | ConvertFrom-Json
            if ($parsed.type -eq "state_transition" -and $parsed.task_id) {
                $knownTaskIds[$parsed.task_id] = $true
            }
        } catch {
            $preview = if ($trimmed.Length -gt 80) { $trimmed.Substring(0, 80) } else { $trimmed }
            $jsonlErrors += "[WARN] JSONL 损坏块 (块 #$blockNum): $preview..."
        }
    }
}

# Append-only 检查：JSONL 中出现过的 task_id 必须在 features.json 中存在
foreach ($knownId in $knownTaskIds.Keys) {
    if (-not $taskStatus.ContainsKey($knownId)) {
        $warnings += "[WARN] ${knownId}: 在 animus-history.jsonl 中存在但 features.json 中已被删除（append-only 违规）"
    }
}

# 汇总 JSONL 错误
if ($jsonlErrors.Count -gt 0) {
    foreach ($e in $jsonlErrors) {
        Write-Host "  $e"
    }
    Write-Host "JSONL 校验: 发现 $($jsonlErrors.Count) 个问题"
}

if ($warnings.Count -gt 0) {
    Write-Host "FAILED: Found $($warnings.Count) inconsistencies"
    foreach ($w in $warnings) { Write-Host "  $w" }
    exit 1
} else {
    Write-Host "PASSED: Consistency check OK ($($taskStatus.Count) tasks, JSONL append-only check passed)"
    exit 0
}

