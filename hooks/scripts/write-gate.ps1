# write-gate.ps1 — PreToolUse 写代码门控
# exit 1 = 阻塞，exit 0 = 放行
# 失败安全：任何解析错误 exit 0（放行）

$ErrorActionPreference = "Stop"

try {
    $inputObj = $input | ConvertFrom-Json
} catch {
    exit 0
}

# 解析操作类型
$operation = if ($inputObj.tool) { $inputObj.tool } else { $inputObj.name }
if (-not $operation) { exit 0 }
if ($operation -notmatch '^(Write|Edit)$') { exit 0 }

# 解析文件路径
$filePath = $inputObj.tool_input.file_path
if (-not $filePath) { exit 0 }
# 统一为正斜杠
$filePath = $filePath -replace '\\', '/'

# 白名单：.claude/ 路径和 .md 文件放行
if ($filePath -match '^\.claude/') { exit 0 }
if ($filePath -match '\.md$') { exit 0 }

# 向上查找 .claude/animus/features.json
$dir = Split-Path $filePath -Parent
$featuresPath = $null

while ($dir -and (Test-Path $dir -PathType Container)) {
    $candidate = Join-Path $dir ".claude/animus/features.json"
    if (Test-Path $candidate) {
        $featuresPath = $candidate
        break
    }
    $parent = Split-Path $dir -Parent
    if ($parent -eq $dir) { break }
    $dir = $parent
}

if (-not $featuresPath) { exit 0 }

# 检查 config.toml 是否关闭门控
$configDirPath = Split-Path $featuresPath -Parent
$configPath = Join-Path $configDirPath "config.toml"

if (Test-Path $configPath) {
    try {
        $configText = Get-Content $configPath -Raw -Encoding UTF8
        # 提取 [gates] 段，查找 require_task_before_write
        $inGates = $false
        $gateDisabled = $false
        foreach ($line in ($configText -split "`r?`n")) {
            $trimmed = $line.Trim()
            if ($trimmed -match '^\[gates\]$') {
                $inGates = $true
                continue
            }
            if ($inGates -and $trimmed -match '^\[') {
                $inGates = $false
                continue
            }
            if ($inGates -and $trimmed -match '^require_task_before_write\s*=\s*(true|false)$') {
                if ($matches[1] -eq 'false') {
                    $gateDisabled = $true
                }
                break
            }
        }
        if ($gateDisabled) { exit 0 }
    } catch {
        # 解析失败，放行
    }
}

# 检查 features.json 有无 in_progress 任务
try {
    $features = Get-Content $featuresPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $tasks = $features.tasks
    if (-not $tasks) {
        $tasks = $features.initial_tasks
    }

    if ($tasks) {
        $hasInProgress = $false
        if ($tasks -is [System.Collections.IDictionary]) {
            foreach ($t in $tasks.Values) {
                if ($t.status -eq 'in_progress') {
                    $hasInProgress = $true
                    break
                }
            }
        } else {
            foreach ($t in $tasks) {
                if ($t.status -eq 'in_progress') {
                    $hasInProgress = $true
                    break
                }
            }
        }
        if ($hasInProgress) { exit 0 }
    }
} catch {
    # 解析失败，放行
    exit 0
}

# 无任务，阻塞
Write-Host "❌ 阻塞：写代码前需要先有 in_progress 任务" -ForegroundColor Red
Write-Host "   请先执行 /animus-dev 完成需求确认和任务拆分" -ForegroundColor Yellow
exit 1
