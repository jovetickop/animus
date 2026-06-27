# PreToolUse 钩子 — Write/Edit 操作前自动备份 features.json 状态文件
# 备份文件名为 features.json.bak.YYYYMMDDHHMMSS，保留最近 5 个备份
# 始终以 exit 0 退出，绝不阻塞操作

# 使用 ConvertFrom-Json 替代脆弱的正则解析 JSON
try {
    $inputObj = $input | ConvertFrom-Json
    $tool = $inputObj.tool
    $name = $inputObj.name
    $filePath = $inputObj.tool_input.file_path
} catch {
    exit 0
}

# 仅处理 Write/Edit 操作
$operation = $tool -or $name
if (-not $operation) { exit 0 }
if ($operation -notmatch '^(Write|Edit)$') { exit 0 }

# 提取被写入的文件路径
if (-not $filePath) { exit 0 }
$filePath = $filePath -replace '\\\\', '\'

# ---- GBK 编码自动转换：Write/Edit 前将 GBK 文件转为 UTF-8 ----
# 检查 project-config.json 中 encoding=gbk，若是则运行 encoding-bridge.py
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
    try {
        $configObj = Get-Content $projectConfig -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($configObj.encoding -eq "gbk" -and $filePath -match '\.(cpp|cc|cxx|c|h|hpp|hxx)$') {
            $bridgeScript = "$PSScriptRoot\encoding-bridge.py"
            if (Test-Path $bridgeScript) {
                python $bridgeScript --action to_utf8 --file $filePath
            }
        }
    } catch {
        # GBK 转换失败不影响写操作
    }
}

# 从目标文件向上遍历目录，查找 .claude/state/features.json
$dir = Split-Path $filePath -Parent
$featuresPath = $null

while ($dir -and (Test-Path $dir)) {
    $candidate = Join-Path $dir ".claude\state\features.json"
    if (Test-Path $candidate) {
        $featuresPath = $candidate
        break
    }
    $parent = Split-Path $dir -Parent
    if ($parent -eq $dir) { break }  # 已到驱动器根目录，停止遍历
    $dir = $parent
}

# 未找到 features.json，无需备份
if (-not $featuresPath) { exit 0 }

# 生成带时间戳的备份文件名：features.json.bak.YYYYMMDDHHMMSS
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$backupDir = Split-Path $featuresPath -Parent
$backupPath = Join-Path $backupDir "features.json.bak.$timestamp"

# 执行备份，失败时静默退出不阻塞写操作
try {
    Copy-Item $featuresPath $backupPath -Force
} catch {
    exit 0
}

# 清理旧备份：只保留按文件名排序最近的 5 个
try {
    $backups = Get-ChildItem (Join-Path $backupDir "features.json.bak.*") | Sort-Object Name -Descending
    if ($backups.Count -gt 5) {
        $backups | Select-Object -Skip 5 | Remove-Item -Force
    }
} catch {
    # 清理失败不影响主流程
}

exit 0
