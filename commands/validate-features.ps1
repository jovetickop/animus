param(
    [string]$FeaturesPath = ".claude/animus/features.json"
)

$ErrorActionPreference = "Stop"
$errors = @()

if (-not (Test-Path $FeaturesPath)) {
    Write-Host "FAILED: File not found: $FeaturesPath"
    exit 1
}

try {
    $data = Get-Content $FeaturesPath -Raw -Encoding utf8 | ConvertFrom-Json
} catch {
    Write-Host "FAILED: JSON parse error: $_"
    exit 1
}

# 支持纯数组格式
if ($data -isnot [array]) {
    if ($data.tasks -is [array]) {
        $data = $data.tasks
    } else {
        Write-Host "FAILED: Root element is neither an array nor an object with 'tasks' array"
        exit 1
    }
}

$requiredFields = @('id','name','status','depends_on','priority','last_error','updated_at')
$validStatuses = @('pending','in_progress','passed','failed')
$allIds = @{}
$inProgressCount = 0

foreach ($task in $data) {
    $id = $task.id

    # Check required fields
    foreach ($field in $requiredFields) {
        if ($null -eq $task.$field -and $task.$field -ne '') {
            $errors += "[ERROR] $($id): Missing required field '$field'"
        }
    }

    # Check ID uniqueness
    if ($allIds.ContainsKey($id)) {
        $errors += "[ERROR] $($id): Duplicate task ID"
    } else {
        $allIds[$id] = $true
    }

    # Check status validity
    if ($task.status -in $validStatuses) {
        if ($task.status -eq 'in_progress') { $inProgressCount++ }
    } else {
        $errors += "[ERROR] $($id): Invalid status '$($task.status)', allowed: $($validStatuses -join ', ')"
    }

    # Check priority
    if ($null -ne $task.priority -and ($task.priority -isnot [int] -or $task.priority -le 0)) {
        $errors += "[ERROR] $($id): priority must be a positive integer"
    }

}

# Check depends_on references
foreach ($task in $data) {
    if ($null -ne $task.depends_on -and $task.depends_on -is [array]) {
        foreach ($depId in $task.depends_on) {
            if (-not $allIds.ContainsKey($depId)) {
                $errors += "[ERROR] $($task.id): depends_on references non-existent task '$depId'"
            }
        }
    }
}

# Check multiple in_progress
if ($inProgressCount -gt 1) {
    $errors += "[ERROR] $inProgressCount tasks are in_progress (only 1 allowed)"
}

if ($errors.Count -gt 0) {
    Write-Host "FAILED: Found $($errors.Count) issues"
    foreach ($err in $errors) { Write-Host "  $err" }
    exit 1
} else {
    Write-Host "PASSED: $($data.Count) tasks, structure validation OK"
    exit 0
}

