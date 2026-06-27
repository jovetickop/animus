param(
    [string]$ProjectRoot = "."
)

# ============================================================
# harness-cc 项目初始化脚本
# 功能：复制完整的工作流资产到目标项目
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

# 确保 ProjectRoot 是绝对路径
if (-not [System.IO.Path]::IsPathRooted($ProjectRoot)) {
    $ProjectRoot = Join-Path (Get-Location) $ProjectRoot
}

# 确保路径使用反斜杠
$ProjectRoot = $ProjectRoot -replace '/', '\'

$ClaudeDir = Join-Path $ProjectRoot ".claude"
$HarnessDir = Join-Path $ClaudeDir "harness"

Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  harness-cc 项目初始化" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "目标目录: $ProjectRoot"
Write-Host ""

# ============================================================
# 步骤 1: 确定技能目录（SKILL.md 所在目录）
# ============================================================
Write-Step "确定 harness-cc 技能目录..."

# 优先使用脚本所在目录（支持自定义安装路径）
# Then fallback to user profile skill directory
$SkillRoot = $PSScriptRoot
if (-not (Test-Path (Join-Path $SkillRoot "SKILL.md"))) {
    $SkillRoot = Join-Path $env:USERPROFILE ".claude\skills\harness-cc"
}

if (-not (Test-Path (Join-Path $SkillRoot "SKILL.md"))) {
    Write-Host "[错误] 无法找到 harness-cc 技能目录" -ForegroundColor Red
    Write-Host "请确保已安装 harness-cc 技能：" -ForegroundColor Red
    Write-Host "git clone https://github.com/jovetickop/Harness-CC.git `"$env:USERPROFILE\.claude\skills\harness-cc`"" -ForegroundColor Yellow
    exit 1
}

$SourceRoot = Join-Path $SkillRoot ".claude"
Write-Success "技能目录: $SourceRoot"

# ============================================================
# 步骤 2: 检查初始化状态
# ============================================================
Write-Step "检查项目初始化状态..."

$NeedFullInit = $false
$NeedCopyAssets = $false

# 检查目录是否有内容（不仅检查是否存在）
function Test-DirHasContent([string]$Path) {
    if (-not (Test-Path $Path)) {
        return $false
    }
    $Items = Get-ChildItem $Path -Force -ErrorAction SilentlyContinue
    return ($Items.Count -gt 0)
}

# 检查 harness 目录是否完整
$RequiredHarnessFiles = @("features.json", "show-status.py", "update-progress.ps1", "run-regression.ps1")
$MissingHarnessFiles = @()
foreach ($File in $RequiredHarnessFiles) {
    $FilePath = Join-Path $HarnessDir $File
    if (-not (Test-Path $FilePath)) {
        $MissingHarnessFiles += $File
    }
}

# 检查是否有任何需要的资产缺失
$HasAgents = Test-DirHasContent (Join-Path $ClaudeDir "agents\universal")
$HasRules = Test-DirHasContent (Join-Path $ClaudeDir "rules\universal")
$HasCommands = Test-Path (Join-Path $ClaudeDir "commands")
$HasHooks = Test-Path (Join-Path $ClaudeDir "hooks")

if (-not (Test-Path $HarnessDir) -or $MissingHarnessFiles.Count -gt 0) {
    Write-Info "harness 目录缺失或文件不完整，需要初始化"
    $NeedFullInit = $true
    $NeedCopyAssets = $true
} elseif (-not ($HasAgents -and $HasRules -and $HasCommands -and $HasHooks)) {
    Write-Info "部分资产缺失，补充复制"
    $NeedFullInit = $false
    $NeedCopyAssets = $true
} else {
    Write-Info "项目已完整初始化，跳过"
    Write-Host ""
    Write-Host "项目状态: 已完成初始化" -ForegroundColor Green
    Write-Host "  - harness: 已安装"
    Write-Host "  - agents: 已安装"
    Write-Host "  - rules: 已安装"
    Write-Host "  - commands: 已安装"
    Write-Host "  - hooks: 已安装"
    Write-Host ""
    Write-Host "使用 /harness-cc 开始工作流" -ForegroundColor Cyan
    exit 0
}

# ============================================================
# 步骤 3: 创建目录结构
# ============================================================
Write-Step "创建 .claude 目录结构..."

$DirsToCreate = @(
    $ClaudeDir,
    (Join-Path $ClaudeDir "agents"),
    (Join-Path $ClaudeDir "agents\universal"),
    (Join-Path $ClaudeDir "rules"),
    (Join-Path $ClaudeDir "rules\universal"),
    (Join-Path $ClaudeDir "commands"),
    (Join-Path $ClaudeDir "hooks"),
    (Join-Path $ClaudeDir "hooks\scripts"),
    (Join-Path $ClaudeDir "skills"),
    $HarnessDir
)

foreach ($Dir in $DirsToCreate) {
    if (-not (Test-Path $Dir)) {
        New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    }
}

Write-Success "目录结构创建完成"

# ============================================================
# 步骤 4: 复制 harness 目录
# ============================================================
Write-Step "复制 harness 状态引擎..."

$SourceHarness = Join-Path $SourceRoot "templates\harness"
$HarnessFiles = @(
    "features.json",
    "project-config.json",
    "claude-progress.txt",
    "show-status.py",
    "update-progress.ps1",
    "run-regression.ps1",
    "coding-session.ps1",
    "README.md"
)

foreach ($File in $HarnessFiles) {
    $Source = Join-Path $SourceHarness $File
    $Dest = Join-Path $HarnessDir $File
    if (Test-Path $Source) {
        Copy-Item $Source $Dest -Force
        Write-Info "  复制: $File"
    } else {
        Write-Warn "  源文件不存在: $File"
    }
}

Write-Success "harness 目录复制完成"

# ============================================================
# 步骤 5: 检测项目类型
# ============================================================
Write-Step "检测项目类型..."

$ProjectType = "generic"

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
} elseif (Test-Path (Join-Path $ProjectRoot "package.json")) {
    $ProjectType = "node"
    Write-Info "检测到: Node.js 项目"
} elseif ((Test-Path (Join-Path $ProjectRoot "pyproject.toml")) -or (Test-Path (Join-Path $ProjectRoot "requirements.txt"))) {
    $ProjectType = "python"
    Write-Info "检测到: Python 项目"
} else {
    Write-Info "检测到: 通用项目"
}

Write-Success "项目类型: $ProjectType"

# ============================================================
# 步骤 6: 复制通用资产
# ============================================================
Write-Step "复制通用资产..."

# 复制 universal agents
$SourceUniversalAgents = Join-Path $SourceRoot "agents\universal"
if (Test-Path $SourceUniversalAgents) {
    $DestUniversalAgents = Join-Path $ClaudeDir "agents\universal"
    Copy-Item "$SourceUniversalAgents\*" $DestUniversalAgents -Force -Recurse
    Write-Info "  agents/universal/ -> .claude/agents/universal/"
}

# 复制 universal rules
$SourceUniversalRules = Join-Path $SourceRoot "rules\universal"
if (Test-Path $SourceUniversalRules) {
    $DestUniversalRules = Join-Path $ClaudeDir "rules\universal"
    Copy-Item "$SourceUniversalRules\*" $DestUniversalRules -Force -Recurse
    Write-Info "  rules/universal/ -> .claude/rules/universal/"
}

# 复制 commands
$SourceCommands = Join-Path $SourceRoot "commands"
if (Test-Path $SourceCommands) {
    $DestCommands = Join-Path $ClaudeDir "commands"
    if (-not (Test-Path $DestCommands)) {
        New-Item -ItemType Directory -Force -Path $DestCommands | Out-Null
    }
    Copy-Item "$SourceCommands\*" $DestCommands -Force -Recurse
    Write-Info "  commands/ -> .claude/commands/"
}

# 复制 hooks
$SourceHooks = Join-Path $SourceRoot "hooks"
if (Test-Path $SourceHooks) {
    $DestHooks = Join-Path $ClaudeDir "hooks"
    Copy-Item "$SourceHooks\*" $DestHooks -Force -Recurse
    Write-Info "  hooks/ -> .claude/hooks/"
}

# 复制 tdd-workflow skill
$SourceTddSkill = Join-Path $SourceRoot "skills\tdd-workflow"
if (Test-Path $SourceTddSkill) {
    $DestTddSkill = Join-Path $ClaudeDir "skills\tdd-workflow"
    if (-not (Test-Path $DestTddSkill)) {
        New-Item -ItemType Directory -Force -Path $DestTddSkill | Out-Null
    }
    Copy-Item "$SourceTddSkill\*" $DestTddSkill -Force -Recurse
    Write-Info "  skills/tdd-workflow/ -> .claude/skills/tdd-workflow/"
} else {
    Write-Warn "  skills/tdd-workflow/ 未找到"
}

Write-Success "通用资产复制完成"

# ============================================================
# 步骤 7: 复制语言专项资产
# ============================================================
Write-Step "复制 $ProjectType 专项资产..."

$TypeMapping = @{
    "cpp-qt" = @{ Agents = "qt"; Rules = "qt" }
    "cpp-cmake" = @{ Agents = "cpp-cmake"; Rules = "cpp-cmake" }
    "python" = @{ Agents = "python"; Rules = "python" }
    "node" = @{ Agents = "node"; Rules = "node" }
    "rust" = @{ Agents = "rust"; Rules = "rust" }
}

if ($TypeMapping.ContainsKey($ProjectType)) {
    $TypeInfo = $TypeMapping[$ProjectType]

    # 复制语言专项 agents
    $SourceTypeAgents = Join-Path $SourceRoot "agents\$($TypeInfo.Agents)"
    if (Test-Path $SourceTypeAgents) {
        $DestTypeAgents = Join-Path $ClaudeDir "agents\$($TypeInfo.Agents)"
        if (-not (Test-Path $DestTypeAgents)) {
            New-Item -ItemType Directory -Force -Path $DestTypeAgents | Out-Null
        }
        Copy-Item "$SourceTypeAgents\*" $DestTypeAgents -Force -Recurse
        Write-Info "  agents/$($TypeInfo.Agents)/ -> .claude/agents/$($TypeInfo.Agents)/"
    }

    # 复制语言专项 rules
    $SourceTypeRules = Join-Path $SourceRoot "rules\$($TypeInfo.Rules)"
    if (Test-Path $SourceTypeRules) {
        $DestTypeRules = Join-Path $ClaudeDir "rules\$($TypeInfo.Rules)"
        if (-not (Test-Path $DestTypeRules)) {
            New-Item -ItemType Directory -Force -Path $DestTypeRules | Out-Null
        }
        Copy-Item "$SourceTypeRules\*" $DestTypeRules -Force -Recurse
        Write-Info "  rules/$($TypeInfo.Rules)/ -> .claude/rules/$($TypeInfo.Rules)/"
    }
}

Write-Success "专项资产复制完成"

# ============================================================
# 步骤 8: 复制根目录配置文件
# ============================================================
Write-Step "复制配置文件到项目根目录..."

# 根目录文件映射
$RootFiles = @{
    "templates\.clang-format" = ".clang-format"
    "templates\.mcp.json" = ".mcp.json"
    "templates\existing_project\review-checklist.md" = "review-checklist.md"
    "templates\existing_project\cmake-adapter.md" = "cmake-adapter.md"
}

foreach ($Mapping in $RootFiles.GetEnumerator()) {
    $Source = Join-Path $SourceRoot $Mapping.Key
    $Dest = Join-Path $ProjectRoot $Mapping.Value
    if ((Test-Path $Source) -and (-not (Test-Path $Dest))) {
        Copy-Item $Source $Dest -Force
        Write-Info "  $($Mapping.Value)"
    }
}

Write-Success "配置文件复制完成"

# ============================================================
# 步骤 9: 处理 CLAUDE.md
# ============================================================
Write-Step "处理 CLAUDE.md..."

$SourceClaudeMd = Join-Path $SourceRoot "templates\existing_project\CLAUDE.md"
$DestClaudeMd = Join-Path $ProjectRoot "CLAUDE.md"

if (Test-Path $SourceClaudeMd) {
    if (Test-Path $DestClaudeMd) {
        # 追加到现有 CLAUDE.md
        $ExistingContent = Get-Content $DestClaudeMd -Encoding UTF8 -Raw
        $TemplateContent = Get-Content $SourceClaudeMd -Encoding UTF8 -Raw

        # 检查是否已有完整的 harness-cc 区块（开+闭标签都存在，大小写不敏感）
        $hasOpenSentinel = $ExistingContent -match "(?i)<!--\s*harness-cc\s*-->"
        $hasCloseSentinel = $ExistingContent -match "(?i)<!--\s*/harness-cc\s*-->"
        $hasCompleteSection = $hasOpenSentinel -and $hasCloseSentinel
        if (-not $hasCompleteSection) {
            $HarnessSection = "`n`n<!-- harness-cc -->`n$TemplateContent`n<!-- /harness-cc -->"
            Add-Content -Path $DestClaudeMd -Value $HarnessSection -Encoding UTF8
            if ($hasOpenSentinel -or $hasCloseSentinel) {
                Write-Info "  检测到不完整的 harness-cc 哨兵，重新追加"
            } else {
                Write-Info "  追加到现有 CLAUDE.md"
            }
        } else {
            Write-Info "  CLAUDE.md 已包含完整 harness-cc 区块，跳过"
        }
    } else {
        # 直接复制模板
        Copy-Item $SourceClaudeMd $DestClaudeMd -Force
        Write-Info "  创建新的 CLAUDE.md"
    }
}

Write-Success "CLAUDE.md 处理完成"

# ============================================================
# 步骤 10: 更新 project-config.json
# ============================================================
Write-Step "更新项目配置..."

$ConfigFile = Join-Path $HarnessDir "project-config.json"
$Today = Get-Date -Format "yyyy-MM-dd"

$Config = @{
    "project-type" = $ProjectType
    "detected-at" = $Today
    "configure-command" = ""
    "build-command" = ""
    "test-command" = ""
    "run-command" = ""
}

# 如果文件已存在，读取现有配置
if (Test-Path $ConfigFile) {
    $ExistingConfig = Get-Content $ConfigFile -Encoding UTF8 | ConvertFrom-Json
    # 保留已填写的命令
    if ($ExistingConfig."configure-command") { $Config."configure-command" = $ExistingConfig."configure-command" }
    if ($ExistingConfig."build-command") { $Config."build-command" = $ExistingConfig."build-command" }
    if ($ExistingConfig."test-command") { $Config."test-command" = $ExistingConfig."test-command" }
    if ($ExistingConfig."run-command") { $Config."run-command" = $ExistingConfig."run-command" }
}

$Config | ConvertTo-Json -Depth 3 | Set-Content $ConfigFile -Encoding UTF8
Write-Success "项目配置已更新: $ProjectType"

# ============================================================
# 完成
# ============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Success "初始化完成!"
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "已安装:" -ForegroundColor Green
Write-Host "  - .claude/harness/       状态引擎"
Write-Host "  - .claude/agents/        Agent 定义"
Write-Host "  - .claude/rules/         编码规范"
Write-Host "  - .claude/commands/      斜杠命令"
Write-Host "  - .claude/hooks/         自动化钩子"
Write-Host "  - .claude/skills/        子技能"
Write-Host ""
Write-Host "项目类型: $ProjectType" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 确认构建/测试命令（编辑 project-config.json）"
Write-Host "  2. 使用 /harness-code-plan 拆解任务"
Write-Host "  3. 使用 /harness-cc 开始工作流"
Write-Host ""
