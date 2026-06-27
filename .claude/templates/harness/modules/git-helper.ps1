# git-helper.ps1 — Git 自动提交模块（仅本地提交，由用户推送）

function Invoke-GitCommit {
    param(
        [Parameter(Mandatory=$true)][string]$FeaturesPath,
        [Parameter(Mandatory=$true)][string]$ProgressPath,
        [Parameter(Mandatory=$true)][string]$ReportPath,
        [Parameter(Mandatory=$true)][string]$TaskId,
        [Parameter(Mandatory=$true)][string]$Status
    )
    git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -ne 0) { Write-Host "非 Git 仓库，跳过自动提交"; return }

    git add -- $FeaturesPath $ProgressPath $ReportPath
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { Write-Host "无可提交变更"; return }

    $commitMessage = "chore(harness): update $TaskId to $Status"
    git commit -m $commitMessage
    if ($LASTEXITCODE -ne 0) { Write-Host "git commit 失败，请人工处理。" }
}
