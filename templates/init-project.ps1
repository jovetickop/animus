param(
    [string]$ProjectRoot = "."
)

# ============================================================
# animus 项目初始化脚本（精简版）
# 功能：创建 .claude\animus\ 目录和配置文件，不再复制文件
# ============================================================

# 中文输出函数
function Write-Step([string]$Message) {
    Write-Host "[步骤] $Message" -ForegroundColor Cyan
}

function Write-Success([string]$Message) {
    Write-Host "[成功] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "[警告] $Message" -ForegroundColor Yellow
}

function Write-Info([string]$Message) {
    Write-Host "[信息] $Message" -ForegroundColor Gray
}

# ============================================================
# 步骤 1: 确定路径
# ============================================================
Write-Step "确定项目路径..."

# 确保 ProjectRoot 是绝对路径
if (-not [System.IO.Path]::IsPathRooted($ProjectRoot)) {
    $ProjectRoot = Join-Path (Get-Location) $ProjectRoot
}

# 斜杠统一为反斜杠
$ProjectRoot = $ProjectRoot -replace '/', '\'

$StateDir  = Join-Path $ProjectRoot ".claude\animus"
$ReportsDir = Join-Path $StateDir "docs"

Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  animus 项目初始化（精简模式）" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "目标目录: $ProjectRoot"
Write-Host ""

# ============================================================
# 步骤 2: 确定技能根目录
# ============================================================
Write-Step "确定 animus 技能目录..."

# 脚本在 templates/ 下，技能根是父目录
$SkillRoot = Split-Path $PSScriptRoot -Parent

if (-not (Test-Path (Join-Path $SkillRoot ".claude-plugin\plugin.json"))) {
    $SkillRoot = Join-Path $env:USERPROFILE ".claude\plugins\animus"
}

if (-not (Test-Path (Join-Path $SkillRoot ".claude-plugin\plugin.json"))) {
    Write-Host "[错误] 无法找到 animus 技能目录" -ForegroundColor Red
    Write-Host "请确保已安装 animus 技能：" -ForegroundColor Red
    Write-Host "git clone https://github.com/jovetickop/Animus.git `"$env:USERPROFILE\.claude\plugins\animus`"" -ForegroundColor Yellow
    exit 1
}

Write-Success "技能目录: $SkillRoot"

# ============================================================
# 步骤 3: 创建目录
# ============================================================
Write-Step "创建 .claude\animus 目录结构..."

New-Item -ItemType Directory -Force -Path $StateDir  | Out-Null
New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null

Write-Success "目录创建完成: $StateDir"

# ============================================================
# 步骤 4: 检测项目类型
# ============================================================
Write-Step "检测项目类型..."

$ProjectType = "generic"

$Today = Get-Date -Format "yyyy-MM-dd"

if (Test-Path (Join-Path $ProjectRoot "CMakeLists.txt")) {
    $CMakeContent = Get-Content (Join-Path $ProjectRoot "CMakeLists.txt") -Raw -Encoding UTF8
    if ($CMakeContent -match "find_package\s*\(\s*Qt") {
        $ProjectType = "cpp-qt"
        Write-Info "检测到: C++/Qt 项目"
    } else {
        $ProjectType = "cpp-cmake"
        Write-Info "检测到: C++/CMake 项目"
    }
} elseif (Test-Path (Join-Path $ProjectRoot "Cargo.toml")) {
    $ProjectType = "rust"
    Write-Info "检测到: Rust 项目"
} elseif (Test-Path (Join-Path $ProjectRoot "go.mod")) {
    $ProjectType = "go"
    Write-Info "检测到: Go 项目"
} elseif (Test-Path (Join-Path $ProjectRoot "package.json")) {
    $ProjectType = "node"
    Write-Info "检测到: Node.js 项目"
} elseif ((Test-Path (Join-Path $ProjectRoot "pyproject.toml")) -or (Test-Path (Join-Path $ProjectRoot "requirements.txt"))) {
    $ProjectType = "python"
    Write-Info "检测到: Python 项目"
} else {
    Write-Info "检测到: 通用项目 (generic)"
}

Write-Success "项目类型: $ProjectType"

# ============================================================
# 步骤 5: 写入 README.md
# ============================================================
Write-Step "写入 README.md..."

$ReadmeFile = Join-Path $StateDir "README.md"

$ReadmeContent = @"
# animus

## 目录位置

- **技能安装目录**: $SkillRoot
- **项目状态目录**: .claude\animus\（本目录）

## 目录结构

```
.claude\animus\
├── README.md                # 本文件
├── features.json            # 任务状态列表
├── animus-history.jsonl    # 结构化日志
├── project-config.json      # 项目配置
└── docs\                    # 任务报告
```

## 工作流命令

### 查看状态
```
python "$SkillRoot/scripts/show-status.py"
```

### 更新任务状态
```
powershell -File "$SkillRoot/scripts/animus-engine.py transition" <TaskId> <status> "描述"
```

### 运行回归测试
```
powershell -File "$SkillRoot/scripts/run-regression.py"
```

### 状态说明
- `pending` - 等待执行
- `in_progress` - 正在执行
- `passed` - 已完成
- `failed` - 失败

## Agent 索引
- 通用 Agent: $SkillRoot/agents/universal/
- 各语言专项: $SkillRoot/agents/{lang}/

## 规则索引
- 通用规则: $SkillRoot/rules/universal/
- 各语言专项: $SkillRoot/rules/{lang}/
"@

if (-not (Test-Path $ReadmeFile)) {
    Set-Content -Path $ReadmeFile -Value $ReadmeContent -Encoding UTF8
    Write-Info "  README.md 已创建"
} else {
    Write-Info "  README.md 已存在，跳过"
}

# ============================================================
# 步骤 6: 写入 project-config.json
# ============================================================
Write-Step "写入 project-config.json..."

$ConfigFile = Join-Path $StateDir "project-config.json"

$Config = @{
    "project-type" = $ProjectType
    "detected-at"  = $Today
    "auto-update-plugin" = $true
    "verify_config" = @{
        "verify_enabled"        = $false
        "verify_command"        = ""
        "verify_timeout_seconds" = 120
    }
    "build-command" = ""
    "test-command"  = ""
    "run-command"   = ""
}

# 如果文件已存在，保留已有的 build/test/run-command 值
if (Test-Path $ConfigFile) {
    $ExistingConfig = Get-Content $ConfigFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($ExistingConfig."build-command") { $Config."build-command" = $ExistingConfig."build-command" }
    if ($ExistingConfig."test-command")  { $Config."test-command"  = $ExistingConfig."test-command" }
    if ($ExistingConfig."run-command")   { $Config."run-command"   = $ExistingConfig."run-command" }
    Write-Info "  project-config.json 已存在，保留已有命令值"
}

$Config | ConvertTo-Json -Depth 3 | Set-Content $ConfigFile -Encoding UTF8
Write-Success "project-config.json 已写入"

# ============================================================
# 步骤 7: 写入 features.json
# ============================================================
Write-Step "写入 features.json..."

$FeaturesFile = Join-Path $StateDir "features.json"

$Features = @()

if (-not (Test-Path $FeaturesFile)) {
    $Features | ConvertTo-Json -Depth 3 | Set-Content $FeaturesFile -Encoding UTF8
    Write-Info "  features.json 已创建"
} else {
    Write-Info "  features.json 已存在，跳过"
}

# ============================================================
# 步骤 8: 写入 animus-history.jsonl
# ============================================================
Write-Step "写入 animus-history.jsonl..."

$HistoryFile = Join-Path $StateDir "animus-history.jsonl"

if (-not (Test-Path $HistoryFile)) {
    Set-Content -Path $HistoryFile -Value "" -Encoding UTF8
    Write-Info "  animus-history.jsonl 已创建"
} else {
    Write-Info "  animus-history.jsonl 已存在，跳过"
}

# ============================================================
# 步骤 9: 完成（不修改项目 CLAUDE.md，不复制任何文件）
# ============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Success "初始化完成!"
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "已创建:" -ForegroundColor Green
Write-Host "  - $StateDir\README.md"
Write-Host "  - $StateDir\features.json"
Write-Host "  - $StateDir\animus-history.jsonl"
Write-Host "  - $StateDir\project-config.json"
Write-Host "  - $StateDir\docs\"
Write-Host ""
Write-Host "项目类型: $ProjectType" -ForegroundColor Cyan
Write-Host "技能目录: $SkillRoot" -ForegroundColor Cyan
Write-Host ""
Write-Host "注意: 本模式仅创建配置文件，Agent/规则/命令/Hook 等资产" -ForegroundColor Yellow
Write-Host "      直接从技能目录读取，不再复制到项目。 " -ForegroundColor Yellow
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 确认构建/测试命令（编辑 project-config.json）"
Write-Host "  2. 使用 /animus-plan 拆解任务"
Write-Host "  3. 使用 /animus 开始工作流"
Write-Host ""
