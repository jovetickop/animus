# Format edited C/C++ files after Claude Code write operations.

$inputJson = $input | Out-String

if ($inputJson -notmatch '"file_path"\s*:\s*"([^"]+)"') { exit 0 }
$filePath = $matches[1] -replace '\\\\', '\'

if ($filePath -notmatch '\.(cpp|cc|cxx|c|h|hpp|hxx)$') { exit 0 }

if (Get-Command clang-format -ErrorAction SilentlyContinue) {
    clang-format -i $filePath
    Write-Host "[clang-format] formatted: $filePath"

    # ---- GBK 编码回写：格式化后将 UTF-8 转回 GBK ----
    # 检查 project-config.json 中 encoding=gbk，若是则运行 encoding-bridge.py
    try {
        $encDir = Split-Path $filePath -Parent
        $projectConfig = $null
        while ($encDir -and (Test-Path $encDir)) {
            $candidate = Join-Path $encDir ".claude\harness\project-config.json"
            if (Test-Path $candidate) {
                $projectConfig = $candidate
                break
            }
            $parent = Split-Path $encDir -Parent
            if ($parent -eq $encDir) { break }
            $encDir = $parent
        }
        if ($projectConfig) {
            $configObj = Get-Content $projectConfig -Raw | ConvertFrom-Json
            if ($configObj.encoding -eq "gbk") {
                $bridgeScript = "$PSScriptRoot\encoding-bridge.py"
                if (Test-Path $bridgeScript) {
                    python $bridgeScript --action to_gbk --file $filePath
                    Write-Host "[encoding-bridge] re-encoded to GBK: $filePath"
                }
            }
        }
    } catch {
        # GBK 回写失败不影响格式化结果
    }
}
