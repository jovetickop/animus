# update-progress.ps1 - 状态机主入口（精简编排器）
# 所有逻辑位于 ./modules/ 子目录

param(
    [Parameter(Position = 0)][string]$TaskId,
    [Parameter(Position = 1)][ValidateSet('pending','in_progress','passed','failed','completed')][string]$Status,
    [Parameter(Position = 2)][string]$Message='',
    [switch]$AutoPush,
    [string]$ProjectRoot='.'
)

if ([string]::IsNullOrWhiteSpace($TaskId) -or [string]::IsNullOrWhiteSpace($Status)) {
    Write-Host '用法: update-progress.ps1 <TaskId> <Status> [Message] [-AutoPush] [-ProjectRoot .]'
    exit 1
}

$modulesDir = Join-Path $PSScriptRoot 'modules'
. (Join-Path $modulesDir 'task-helpers.ps1')
. (Join-Path $modulesDir 'validate-transition.ps1')
. (Join-Path $modulesDir 'oracle-runner.ps1')
. (Join-Path $modulesDir 'report-generator.ps1')
. (Join-Path $modulesDir 'git-helper.ps1')

$ClaudeRoot = Join-Path $ProjectRoot '.claude'
$FeaturesPath = Join-Path $ClaudeRoot 'state\features.json'
$ProgressPath = Join-Path $ClaudeRoot 'state\claude-progress.txt'

$features = Read-FeaturesJson -FeaturesPath $FeaturesPath
if (-not $features) { exit 1 }

$tasks = Normalize-Tasks -Features $features
$targetTask = Find-TaskById -Tasks $tasks -TaskId $TaskId
if (-not $targetTask) { Write-Host ("未找到任务 " + $TaskId); exit 1 }

$currentStatus = [string]$targetTask.status
Test-TransitionValid -TargetTask $targetTask -NewStatus $Status -Tasks $tasks

$finalStatus = $Status
$finalMessage = $Message
if ($Status -eq 'passed') {
    $verifyResult = Invoke-OracleVerify -Features $features -TaskId $TaskId -ProgressPath $ProgressPath
    if ($verifyResult.Failed) { $finalStatus = 'failed'; $finalMessage = $verifyResult.Message }
}

$targetTask.status = $finalStatus
$targetTask.updated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$targetTask.last_error = if ($finalStatus -eq 'failed') { $finalMessage } else { '' }

$features | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $FeaturesPath -Encoding UTF8

$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$logLine = "$timestamp | $TaskId | $currentStatus -> $finalStatus | $finalMessage"
Add-Content -LiteralPath $ProgressPath -Value $logLine

$reportPath = Write-TaskReport -Task $targetTask -ProjectRoot $ProjectRoot -ProgressPath $ProgressPath -CurrentStatus $currentStatus -NewStatus $finalStatus -LogMessage $finalMessage

Write-Host ("已将 " + ($TaskId) + " 从 " + ($currentStatus) + " 更新为 " + ($finalStatus))
Write-Host ("已输出任务报告: " + ($reportPath))

if ($AutoPush) { Invoke-GitCommit -FeaturesPath $FeaturesPath -ProgressPath $ProgressPath -ReportPath $reportPath -TaskId $TaskId -Status $finalStatus }
