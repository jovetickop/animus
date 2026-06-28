param(
    [string]$StateDir = ".claude/harness-cc"
)

$ErrorActionPreference = "Stop"
$warnings = @()

$featuresPath = Join-Path $StateDir "features.json"
$progressPath = Join-Path $StateDir "claude-progress.txt"
$historyPath = Join-Path $StateDir "harness-history.jsonl"

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
    $data = $data.tasks
}
foreach ($task in $data) {
    $taskStatus[$task.id] = @{
        status = $task.status
        updated_at = if ($task.updated_at) { $task.updated_at } else { "" }
    }
}

# Read claude-progress.txt
$progressStatus = @{}
if (Test-Path $progressPath) {
    $lines = Get-Content $progressPath -Encoding UTF8
    foreach ($line in $lines) {
        # Match patterns: Txxx -> status, Txxx: status, Txxx = status
        if ($line -match '(T\d{3})\s*(->|:|=)\s*(\w+)') {
            $progressStatus[$matches[1]] = $matches[3]
        }
    }
}

# Compare: features.json has entries not in progress.txt
foreach ($id in $taskStatus.Keys) {
    $jsonStatus = $taskStatus[$id].status
    $progStatus = $progressStatus[$id]

    if (-not $progStatus) {
        if ($jsonStatus -ne 'pending') {
            $warnings += "[WARN] ${id}: features.json=$jsonStatus, progress.txt=NO RECORD"
        }
    } elseif ($jsonStatus -ne $progStatus) {
        $warnings += "[WARN] ${id}: features.json=$jsonStatus, progress.txt=$progStatus"
    }
}

# Reverse check: progress.txt has entries not in features.json
foreach ($id in $progressStatus.Keys) {
    if (-not $taskStatus.ContainsKey($id)) {
        $warnings += "[WARN] ${id}: features.json=NOT FOUND, progress.txt=$($progressStatus[$id])"
    }
}

# JSONL 校验：检测损坏行 + append-only 检查
$jsonlErrors = @()
$knownTaskIds = @{}
if (Test-Path $historyPath) {
    $lines = Get-Content $historyPath -Encoding UTF8
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $parsed = $line | ConvertFrom-Json
            if ($parsed.type -eq "state_transition" -and $parsed.task_id) {
                $knownTaskIds[$parsed.task_id] = $true
            }
        } catch {
            $jsonlErrors += "[WARN] JSONL 损坏行 (行号 $($lines.IndexOf($line) + 1)): $($line.Substring(0, [Math]::Min(80, $line.Length)))..."
        }
    }
}

# Append-only 检查：JSONL 中出现过的 task_id 必须在 features.json 中存在
foreach ($knownId in $knownTaskIds.Keys) {
    if (-not $taskStatus.ContainsKey($knownId)) {
        $warnings += "[WARN] ${knownId}: 在 harness-history.jsonl 中存在但 features.json 中已被删除（append-only 违规）"
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

