# task-helpers.ps1 — 任务辅助模块

function Ensure-TaskField {
    param([Parameter(Mandatory=$true)][object]$Task,[Parameter(Mandatory=$true)][string]$Name,$Value)
    if (-not $Task.PSObject.Properties[$Name]) { $Task | Add-Member -NotePropertyName $Name -NotePropertyValue $Value }
}

function Read-FeaturesJson {
    param([Parameter(Mandatory=$true)][string]$FeaturesPath)
    if (-not (Test-Path $FeaturesPath)) { Write-Host "未找到 features.json: $FeaturesPath"; return $null }
    return Get-Content -Raw -LiteralPath $FeaturesPath -Encoding UTF8 | ConvertFrom-Json
}

function Normalize-Tasks {
    param([Parameter(Mandatory=$true)][object]$Features)
    $tasks = @()
    if ($Features -is [PSCustomObject]) {
        if ($Features.initial_tasks) { $tasks = @($Features.initial_tasks) }
        elseif ($Features.tasks) { $tasks = @($Features.tasks) }
    } elseif ($Features -is [Array]) { $tasks = $Features }
    foreach ($task in $tasks) {
        Ensure-TaskField -Task $task -Name "depends_on" -Value @()
        Ensure-TaskField -Task $task -Name "priority" -Value 0
        Ensure-TaskField -Task $task -Name "last_error" -Value ""
        Ensure-TaskField -Task $task -Name "updated_at" -Value ""
        try { $task.priority = [int]$task.priority } catch { $task.priority = 0 }
        $deps = @(); foreach ($dep in @($task.depends_on)) { $d = [string]$dep; if (-not [string]::IsNullOrWhiteSpace($d)) { $deps += $d.Trim() } }; $task.depends_on = $deps
    }
    return $tasks
}

function Find-TaskById {
    param([Parameter(Mandatory=$true)][object[]]$Tasks,[Parameter(Mandatory=$true)][string]$TaskId)
    return $Tasks | Where-Object { $_.id -eq $TaskId } | Select-Object -First 1
}
