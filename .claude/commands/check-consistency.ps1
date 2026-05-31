param(
    [string]$StateDir = ".claude/state"
)

$ErrorActionPreference = "Stop"
$warnings = @()

$featuresPath = Join-Path $StateDir "features.json"
$progressPath = Join-Path $StateDir "claude-progress.txt"

if (-not (Test-Path $featuresPath)) {
    Write-Host "FAILED: features.json not found: $featuresPath"
    exit 1
}

# Read features.json
try {
    $data = Get-Content $featuresPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "FAILED: Cannot parse features.json: $_"
    exit 1
}

$taskStatus = @{}
foreach ($task in $data) {
    $taskStatus[$task.id] = @{
        status = $task.status
        updated_at = if ($task.updated_at) { $task.updated_at } else { "" }
    }
}

# Read claude-progress.txt
$progressStatus = @{}
if (Test-Path $progressPath) {
    $lines = Get-Content $progressPath
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
            $warnings += "[WARN] $id: features.json=$jsonStatus, progress.txt=NO RECORD"
        }
    } elseif ($jsonStatus -ne $progStatus) {
        $warnings += "[WARN] $id: features.json=$jsonStatus, progress.txt=$progStatus"
    }
}

# Reverse check: progress.txt has entries not in features.json
foreach ($id in $progressStatus.Keys) {
    if (-not $taskStatus.ContainsKey($id)) {
        $warnings += "[WARN] $id: features.json=NOT FOUND, progress.txt=$($progressStatus[$id])"
    }
}

if ($warnings.Count -gt 0) {
    Write-Host "FAILED: Found $($warnings.Count) inconsistencies"
    foreach ($w in $warnings) { Write-Host "  $w" }
    exit 1
} else {
    Write-Host "PASSED: Consistency check OK ($($taskStatus.Count) tasks)"
    exit 0
}
