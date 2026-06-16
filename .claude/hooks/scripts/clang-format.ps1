# Format edited C/C++ files after Claude Code write operations.

# 使用 ConvertFrom-Json 替代脆弱的正则解析 JSON
try {
    $inputObj = $input | ConvertFrom-Json
    $filePath = $inputObj.tool_input.file_path
    if (-not $filePath) { exit 0 }
} catch {
    exit 0
}
$filePath = $filePath -replace '\\\\', '\'

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
            # 优先在用户项目的 .claude/harness/ 下查找
            $candidate = Join-Path $encDir ".claude\harness\project-config.json"
            # 回退到源仓库的 templates/harness/（用于在 harness-cc 源仓库内开发）
            if (-not (Test-Path $candidate)) {
                $candidate = Join-Path $encDir ".claude\templates\harness\project-config.json"
            }
            if (Test-Path $candidate) {
                $projectConfig = $candidate
                break
            }
            $parent = Split-Path $encDir -Parent
            if ($parent -eq $encDir) { break }
            $encDir = $parent
        }
        if ($projectConfig) {
            $configObj = Get-Content $projectConfig -Raw -Encoding UTF8 | ConvertFrom-Json
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
