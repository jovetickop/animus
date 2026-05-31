param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectDir,
    [Parameter(Mandatory=$true)]
    [string]$SkillDir
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

Write-Progress -Activity "CodeHarness Setup" -Status "Detecting project type" -PercentComplete 5

# === 1. Detect project type ===
$projectType = "generic"
$cmakeFile = Join-Path $ProjectDir "CMakeLists.txt"
$cargoFile = Join-Path $ProjectDir "Cargo.toml"
$pkgFile = Join-Path $ProjectDir "package.json"
$pyprojectFile = Join-Path $ProjectDir "pyproject.toml"
$reqFile = Join-Path $ProjectDir "requirements.txt"

if (Test-Path $cmakeFile) {
    $content = Get-Content $cmakeFile -Raw
    if ($content -match 'find_package\(Qt') {
        $projectType = "cpp-qt"
    } else {
        $projectType = "cpp-cmake"
    }
} elseif (Test-Path $cargoFile) {
    $projectType = "rust"
} elseif (Test-Path $pkgFile) {
    $projectType = "node"
} elseif (Test-Path $pyprojectFile -or (Test-Path $reqFile)) {
    $projectType = "python"
}

Write-Host "[harness] Detected project type: $projectType"

# === 2. Build target paths ===
$targetClaude = Join-Path $ProjectDir ".claude"

# === 3. Always-copied source directories ===
# 排除 features.json 和 claude-progress.txt——它们是项目状态数据，不能覆盖
$excludeStateFiles = @('features.json', 'claude-progress.txt')
$alwaysCopy = @(
    @{Src=".claude/templates/harness";       Dst="harness"}
    @{Src=".claude/agents/universal";       Dst="agents/universal"}
    @{Src=".claude/rules/universal";        Dst="rules/universal"}
    @{Src=".claude/commands";               Dst="commands"}
    @{Src=".claude/skills/tdd-workflow";    Dst="skills/tdd-workflow"}
    @{Src=".claude/hooks";                  Dst="hooks"}
)

Write-Progress -Activity "CodeHarness Setup" -Status "Copying common files" -PercentComplete 20
$fileCount = 0

foreach ($item in $alwaysCopy) {
    $srcDir = Join-Path $SkillDir $item.Src
    $dstDir = Join-Path $targetClaude $item.Dst
    if (Test-Path $srcDir) {
        if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
        # 对 harness 目录排除项目状态文件，防止覆盖已有数据
        if ($item.Dst -eq "harness") {
            Copy-Item -Path "$srcDir/*" -Destination $dstDir -Recurse -Force -Exclude $excludeStateFiles
        } else {
            Copy-Item -Path "$srcDir/*" -Destination $dstDir -Recurse -Force
        }
        $count = (Get-ChildItem -Path "$srcDir/*" -Recurse -File).Count
        $fileCount += $count
        Write-Host "[harness]   Copied $($item.Src) -> $dstDir ($count files)"
    }
}

# 仅首次安装时创建 features.json 和 claude-progress.txt
$stateFiles = @(
    @{Name="features.json"; Src=".claude/templates/state/features.json"; Dst="state/features.json"}
    @{Name="claude-progress.txt"; Src=".claude/templates/state/claude-progress.txt"; Dst="state/claude-progress.txt"}
)
foreach ($item in $stateFiles) {
    $src = Join-Path $SkillDir $item.Src
    $dst = Join-Path $targetClaude $item.Dst
    if (-not (Test-Path $dst) -and (Test-Path $src)) {
        Copy-Item $src $dst
        $fileCount++
        Write-Host "[harness]   Created $($item.Name) (first install)"
    }
}

# === 4. Type-specific copy ===
# 注意：源路径在技能目录下（含 .claude/），目的路径相对于项目 .claude/ 目录（不含 .claude/）
$typeAgents = @{
    "cpp-qt"    = @{Src=".claude/agents/qt";    Dst="agents/qt";    SrcRules=".claude/rules/qt";    DstRules="rules/qt"}
    "cpp-cmake" = @{Src=".claude/agents/cpp-cmake"; Dst="agents/cpp-cmake"; SrcRules=".claude/rules/cpp-cmake"; DstRules="rules/cpp-cmake"}
    "python"    = @{Src=".claude/agents/python"; Dst="agents/python"; SrcRules=".claude/rules/python"; DstRules="rules/python"}
    "node"      = @{Src=".claude/agents/node";   Dst="agents/node";   SrcRules=".claude/rules/node";   DstRules="rules/node"}
    "rust"      = @{Src=".claude/agents/rust";   Dst="agents/rust";   SrcRules=".claude/rules/rust";   DstRules="rules/rust"}
}

Write-Progress -Activity "CodeHarness Setup" -Status "Copying type-specific files" -PercentComplete 50

if ($typeAgents.ContainsKey($projectType)) {
    $spec = $typeAgents[$projectType]
    # 复制 agents
    $srcAgents = Join-Path $SkillDir $spec.Src
    $dstAgents = Join-Path $targetClaude $spec.Dst
    if (Test-Path $srcAgents) {
        if (-not (Test-Path $dstAgents)) { New-Item -ItemType Directory -Path $dstAgents -Force | Out-Null }
        Copy-Item -Path "$srcAgents/*" -Destination $dstAgents -Recurse -Force
        $count = (Get-ChildItem -Path "$srcAgents/*" -Recurse -File).Count
        $fileCount += $count
        Write-Host "[harness]   Copied agents ($($spec.Src)) -> $dstAgents ($count files)"
    }
    # 复制 rules
    $srcRules = Join-Path $SkillDir $spec.SrcRules
    $dstRules = Join-Path $targetClaude $spec.DstRules
    if (Test-Path $srcRules) {
        if (-not (Test-Path $dstRules)) { New-Item -ItemType Directory -Path $dstRules -Force | Out-Null }
        Copy-Item -Path "$srcRules/*" -Destination $dstRules -Recurse -Force
        $count = (Get-ChildItem -Path "$srcRules/*" -Recurse -File).Count
        $fileCount += $count
        Write-Host "[harness]   Copied rules ($($spec.SrcRules)) -> $dstRules ($count files)"
    }
}

# === 5. Generate project-config.json ===
Write-Progress -Activity "CodeHarness Setup" -Status "Generating config" -PercentComplete 80

$configPath = Join-Path $targetClaude "harness/project-config.json"
$claudeFile = Join-Path $ProjectDir "CLAUDE.md"   # 步骤 6 也会用到，在此统一定义

# 如果已存在配置文件，保留用户已有的命令值，仅更新项目类型和检测时间
if (Test-Path $configPath) {
    try {
        $existingConfig = Get-Content $configPath -Raw -Encoding utf8 | ConvertFrom-Json
        # 仅当读取到的命令非空时才保留，否则使用默认值
        $buildCmd = if ($existingConfig.'build-command') { $existingConfig.'build-command' } else { "cmake --build build --config Debug" }
        $testCmd = if ($existingConfig.'test-command') { $existingConfig.'test-command' } else { "ctest --test-dir build -C Debug --output-on-failure" }
        $runCmd = if ($existingConfig.'run-command') { $existingConfig.'run-command' } else { "./build/Backgammon.exe" }
        Write-Host "[harness]   Preserved existing project-config.json commands"
    } catch {
        Write-Host "[harness]   Could not read existing project-config.json, using defaults"
        $buildCmd = "cmake --build build --config Debug"
        $testCmd = "ctest --test-dir build -C Debug --output-on-failure"
        $runCmd = "./build/Backgammon.exe"
    }
} else {
    # 首次安装：从 CLAUDE.md 派生默认命令
    $buildCmd = "cmake --build build --config Debug"
    $testCmd = "ctest --test-dir build -C Debug --output-on-failure"
    $runCmd = "./build/Backgammon.exe"

    if (Test-Path $claudeFile) {
        $claudeContent = Get-Content $claudeFile -Raw
        if ($claudeContent -match '(?<=构建命令：`)([^`]+)') { $buildCmd = $matches[1] }
        if ($claudeContent -match '(?<=测试命令：`)([^`]+)') { $testCmd = $matches[1] }
        if ($claudeContent -match '(?<=运行命令：`)([^`]+)') { $runCmd = $matches[1] }
    }
}

$config = @{
    "project-type"  = $projectType
    "detected-at"   = (Get-Date -Format "yyyy-MM-dd")
    "build-command" = $buildCmd
    "test-command"  = $testCmd
    "run-command"   = $runCmd
} | ConvertTo-Json

$config | Out-File -FilePath $configPath -Encoding utf8
Write-Host "[harness]   Generated project-config.json: $projectType"

# === 6. Handle CLAUDE.md merge ===
Write-Progress -Activity "CodeHarness Setup" -Status "Checking CLAUDE.md" -PercentComplete 90

if (-not (Test-Path $claudeFile)) {
    $templateClaude = Join-Path $SkillDir ".claude/templates/existing_project/CLAUDE.md"
    if (Test-Path $templateClaude) {
        Copy-Item $templateClaude $claudeFile
        Write-Host "[harness]   Created CLAUDE.md from template"
    }
} else {
    $claudeContent = Get-Content $claudeFile -Raw
    if ($claudeContent -notmatch "CodeHarness|harness-cc") {
        $harnessBlock = @"

## CodeHarness Workflow

### Session Init
```powershell
.\.claude\harness\coding-session.ps1
python .claude/harness/show-status.py
Get-Content .claude/harness/claude-progress.txt -Tail 20 -Encoding UTF8
```

### Task State Transitions
- Start task: `.\.claude\harness\update-progress.ps1 <TaskId> in_progress "description"`
- Complete task: `.\.claude\harness\update-progress.ps1 <TaskId> passed "description"`
- Mark failed: `.\.claude\harness\update-progress.ps1 <TaskId> failed "reason"`
"@
        Add-Content -Path $claudeFile -Value $harnessBlock
        Write-Host "[harness]   Appended CodeHarness block to CLAUDE.md"
    } else {
        Write-Host "[harness]   CLAUDE.md already has CodeHarness content, skipped"
    }
}

# === 7. Migration: 检测旧路径状态文件并迁移 ===
Write-Progress -Activity "CodeHarness Setup" -Status "Migrating old state files" -PercentComplete 95

$oldFeatures = Join-Path $targetClaude "harness/features.json"
$oldProgress = Join-Path $targetClaude "harness/claude-progress.txt"
$stateDir = Join-Path $targetClaude "state"
$needsMigration = $false

if ((Test-Path $oldFeatures) -and -not (Test-Path (Join-Path $stateDir "features.json"))) {
    if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
    Move-Item $oldFeatures (Join-Path $stateDir "features.json") -Force
    Write-Host "[harness]   Migrated: harness/features.json -> state/features.json"
    $needsMigration = $true
}
if ((Test-Path $oldProgress) -and -not (Test-Path (Join-Path $stateDir "claude-progress.txt"))) {
    if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
    Move-Item $oldProgress (Join-Path $stateDir "claude-progress.txt") -Force
    Write-Host "[harness]   Migrated: harness/claude-progress.txt -> state/claude-progress.txt"
    $needsMigration = $true
}
if ($needsMigration) {
    Write-Host "[harness]   状态文件迁移完成。请更新 CLAUDE.md 中的路径引用。"
}

# === 8. Done ===
$elapsed = [DateTime](Get-Date) - [DateTime]$startTime
Write-Host ""
Write-Host "============================================"
Write-Host "  CodeHarness Setup Complete"
Write-Host "  Project type: $projectType"
Write-Host "  Files copied: $fileCount"
Write-Host "  Elapsed: $($elapsed.TotalSeconds.ToString('0.0'))s"
Write-Host "============================================"
Write-Host ""
Write-Host "Next: run .\.claude\harness\coding-session.ps1 to start working"
