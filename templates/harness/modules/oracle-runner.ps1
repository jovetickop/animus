# oracle-runner.ps1 — Oracle 验证模块
# 执行构建/测试命令，验证状态机状态转换是否被批准

function Invoke-OracleVerify {
    param(
        [Parameter(Mandatory = $true)][object]$Features,
        [Parameter(Mandatory = $true)][string]$TaskId,
        [Parameter(Mandatory = $true)][string]$ProgressPath
    )
    $verifyConfig = $null
    if ($Features -is [PSCustomObject]) { $verifyConfig = $Features.verify_config }

    if (-not $verifyConfig) { return @{ Failed = $false } }

    $verifyEnabled = [bool]($verifyConfig.verify_enabled -eq $true)
    $verifyCommand = [string]$verifyConfig.verify_command

    if (-not ($verifyEnabled -and (-not [string]::IsNullOrWhiteSpace($verifyCommand)))) {
        return @{ Failed = $false }
    }

    Write-Host "[Oracle 验证] 验证命令已配置，开始执行验证..."
    Write-Host "命令: $verifyCommand"

    $verifyTempOut = Join-Path $env:TEMP "harness-verify-$([System.IO.Path]::GetRandomFileName()).txt"
    $verifyTempErr = Join-Path $env:TEMP "harness-verify-err-$([System.IO.Path]::GetRandomFileName()).txt"
    $verifyExitCode = -1; $verifyOutput = ""; $verifyError = ""

    try {
        $process = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-Command",$verifyCommand -NoNewWindow -PassThru -Wait -RedirectStandardOutput $verifyTempOut -RedirectStandardError $verifyTempErr
        $verifyExitCode = $process.ExitCode
        if (Test-Path $verifyTempOut) { $verifyOutput = Get-Content -Raw -LiteralPath $verifyTempOut -Encoding UTF8; Remove-Item $verifyTempOut -Force -ErrorAction SilentlyContinue }
        if (Test-Path $verifyTempErr) { $verifyError = Get-Content -Raw -LiteralPath $verifyTempErr -Encoding UTF8; Remove-Item $verifyTempErr -Force -ErrorAction SilentlyContinue }
    } catch {
        $verifyExitCode = -1; $verifyOutput = ""; $verifyError = "验证命令执行异常: $_"
    }

    $verifyTimestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $verifyLog = @("", "--- Oracle 验证门 ---", "时间: $verifyTimestamp", "任务: $TaskId -> passed", "验证命令: $verifyCommand", "退出码: $verifyExitCode")
    if (-not [string]::IsNullOrWhiteSpace($verifyOutput)) { $verifyLog += "标准输出:"; $verifyLog += $verifyOutput.Trim() }
    if (-not [string]::IsNullOrWhiteSpace($verifyError)) { $verifyLog += "错误输出:"; $verifyLog += $verifyError.Trim() }
    Add-Content -LiteralPath $ProgressPath -Value (($verifyLog -join "`r`n"))

    if ($verifyExitCode -ne 0) {
        Write-Host "[Oracle 验证] 未通过 (exit code: $verifyExitCode)，状态将被设为 failed"
        $failureDetail = "Oracle 验证门拒绝: 验证命令返回非零退出码 ($verifyExitCode)"
        if (-not [string]::IsNullOrWhiteSpace($verifyError)) { $failureDetail += "`r`n" + $verifyError.Trim() }
        return @{ Failed = $true; Message = $failureDetail }
    }
    Write-Host "[Oracle 验证] 通过"
    return @{ Failed = $false }
}
