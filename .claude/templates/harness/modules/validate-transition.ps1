# validate-transition.ps1 — 状态机转换校验模块
# 提供状态转换合法性检查、并发冲突检查、依赖检查

function Test-TransitionValid {
    param(
        [Parameter(Mandatory = $true)][object]$TargetTask,
        [Parameter(Mandatory = $true)][ValidateSet("pending","in_progress","passed","failed","completed")][string]$NewStatus,
        [Parameter(Mandatory = $true)][object[]]$Tasks
    )
    $currentStatus = [string]$TargetTask.status
    switch ($NewStatus) {
        "in_progress" {
            if ($currentStatus -notin @("pending","failed","in_progress","completed")) {
                Write-Host "非法状态流转: $($TargetTask.id) 不允许从 $currentStatus 变为 in_progress"; exit 1
            }
            if ($currentStatus -ne "in_progress") {
                Check-InProgressConflict -TargetTask $TargetTask -Tasks $Tasks
                Check-DependsOnMet -TargetTask $TargetTask -Tasks $Tasks
            }
        }
        "passed" {
            if ($currentStatus -notin @("in_progress","completed")) {
                Write-Host "非法状态流转: $($TargetTask.id) 只能从 in_progress 或 completed 变为 passed"; exit 1
            }
        }
        "completed" {
            if ($currentStatus -eq "pending") { }
            elseif ($currentStatus -notin @("in_progress","passed","completed")) {
                Write-Host "非法状态流转: $($TargetTask.id) 不允许从 $currentStatus 变为 completed"; exit 1
            }
        }
        "failed" {
            if ($currentStatus -eq "pending") { }
            elseif ($currentStatus -ne "in_progress") {
                Write-Host "非法状态流转: $($TargetTask.id) 只能从 in_progress 变为 failed"; exit 1
            }
        }
        "pending" {
            if ($currentStatus -notin @("failed","in_progress","pending","completed")) {
                Write-Host "非法状态流转: $($TargetTask.id) 不允许从 $currentStatus 变为 pending"; exit 1
            }
        }
    }
}

function Check-InProgressConflict {
    param([Parameter(Mandatory=$true)][object]$TargetTask,[Parameter(Mandatory=$true)][object[]]$Tasks)
    $otherInProgress = @($Tasks | Where-Object { $_.id -ne $TargetTask.id -and $_.status -eq "in_progress" })
    if ($otherInProgress.Count -gt 0) {
        $otherIds = ($otherInProgress | ForEach-Object { $_.id }) -join ", "
        Write-Host "状态冲突: 已存在进行中任务 ($otherIds)。请先处理完成或回退后再切换 $($TargetTask.id)。"
        exit 1
    }
}

function Check-DependsOnMet {
    param([Parameter(Mandatory=$true)][object]$TargetTask,[Parameter(Mandatory=$true)][object[]]$Tasks)
    $taskById = @{}; foreach ($task in $Tasks) { $taskById[[string]$task.id] = $task }
    $missingDeps = @(); $unmetDeps = @()
    foreach ($depId in @($TargetTask.depends_on)) {
        if (-not $taskById.ContainsKey($depId)) { $missingDeps += $depId; continue }
        if ([string]$taskById[$depId].status -notin @("passed","completed")) { $unmetDeps += $depId }
    }
    if ($missingDeps.Count -gt 0) { Write-Host ("依赖配置错误: 任务 {0} 引用了不存在的 depends_on: {1}" -f $TargetTask.id,($missingDeps -join ", ")); exit 1 }
    if ($unmetDeps.Count -gt 0) { Write-Host ("依赖未满足: 任务 {0} 仍需等待 {1} 先通过" -f $TargetTask.id,($unmetDeps -join ", ")); exit 1 }
}
