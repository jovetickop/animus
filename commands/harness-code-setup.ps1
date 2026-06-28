param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectDir,
    [Parameter(Mandatory=$true)]
    [string]$PluginRoot
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

Write-Progress -Activity "harness-cc Setup" -Status "Detecting project type" -PercentComplete 5

# === 1. 检测项目类型 ===
$projectType = "generic"
$cmakeFile = Join-Path $ProjectDir "CMakeLists.txt"
$cargoFile = Join-Path $ProjectDir "Cargo.toml"
$pkgFile = Join-Path $ProjectDir "package.json"
$pyprojectFile = Join-Path $ProjectDir "pyproject.toml"
$reqFile = Join-Path $ProjectDir "requirements.txt"
$goModFile = Join-Path $ProjectDir "go.mod"

if (Test-Path $cmakeFile) {
    $content = Get-Content $cmakeFile -Raw
    if ($content -match 'find_package\(Qt') {
        $projectType = "cpp-qt"
    } else {
        $projectType = "cpp-cmake"
    }
} elseif (Test-Path $cargoFile) {
    # Cargo.toml 优先级高于 go.mod
    $projectType = "rust"
} elseif (Test-Path $goModFile) {
    $projectType = "go"
} elseif (Test-Path $pkgFile) {
    $projectType = "node"
} elseif ((Test-Path $pyprojectFile) -or (Test-Path $reqFile)) {
    $projectType = "python"
}

Write-Host "[harness] Detected project type: $projectType"

# === 2. 计算路径 ===
$StateDir = Join-Path $ProjectDir ".claude\harness-cc"
$ReportsDir = Join-Path $StateDir "docs\reports"

Write-Progress -Activity "harness-cc Setup" -Status "Creating directories" -PercentComplete 15

# === 3. 创建目录 ===
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null
Write-Host "[harness]   Created state directory: $StateDir"

# === 4. 清理旧 README.md（已废弃，不再生成） ===
Write-Progress -Activity "harness-cc Setup" -Status "Preparing state" -PercentComplete 30

# 如果存在旧 README.md，清理掉
$readmePath = Join-Path $StateDir "README.md"
if (Test-Path $readmePath) {
    Remove-Item $readmePath -Force
    Write-Host "[harness]   Removed obsolete README.md"
}

}

# === 5. 写入 project-config.json ===
Write-Progress -Activity "harness-cc Setup" -Status "Writing project config" -PercentComplete 50

$configPath = Join-Path $StateDir "project-config.json"
$config = @{
    "project-type"  = $projectType
    "detected-at"   = (Get-Date -Format "yyyy-MM-dd")
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

# 如果文件已存在，保留现有命令配置
if (Test-Path $configPath) {
    try {
        $existingConfig = Get-Content $configPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($existingConfig.'build-command') { $config.'build-command' = $existingConfig.'build-command' }
        if ($existingConfig.'test-command')  { $config.'test-command'  = $existingConfig.'test-command' }
        if ($existingConfig.'run-command')   { $config.'run-command'   = $existingConfig.'run-command' }
        Write-Host "[harness]   Preserved existing project-config.json commands"
    } catch {
        Write-Host "[harness]   Could not read existing project-config.json, using defaults"
    }
}

$configJson = $config | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($configPath, $configJson)
Write-Host "[harness]   Generated project-config.json: $projectType"

# === 6. 初始化 features.json（如果不存在） ===
Write-Progress -Activity "harness-cc Setup" -Status "Initializing features" -PercentComplete 70

$featuresPath = Join-Path $StateDir "features.json"
if (-not (Test-Path $featuresPath)) {
    $features = @()
    $featuresJson = $features | ConvertTo-Json
    [System.IO.File]::WriteAllText($featuresPath, $featuresJson)
    Write-Host "[harness]   Initialized features.json"
} else {
    Write-Host "[harness]   features.json already exists, skipped"
}

# === 7. 初始化 domain-lexicon.md（如果不存在） ===
Write-Progress -Activity "harness-cc Setup" -Status "Initializing domain lexicon" -PercentComplete 80

$lexiconPath = Join-Path $StateDir "domain-lexicon.md"
if (-not (Test-Path $lexiconPath)) {
    $lexiconHeader = @"
# 领域术语表（迭代 I1）

| 术语 | 英文 | 定义 | 别名 | 来源 |
|------|------|------|------|------|

"@
    [System.IO.File]::WriteAllText($lexiconPath, $lexiconHeader)
    Write-Host "[harness]   Initialized domain-lexicon.md"
} else {
    Write-Host "[harness]   domain-lexicon.md already exists, skipped"
}

# === 8. 旧状态文件迁移 ===
Write-Progress -Activity "harness-cc Setup" -Status "Migrating old state files" -PercentComplete 90

$oldPaths = @(
    @{Src = Join-Path $ProjectDir ".claude\harness\features.json"}
    @{Src = Join-Path $ProjectDir ".claude\state\features.json"}
)

$migrationDone = $false
foreach ($item in $oldPaths) {
    $src = $item.Src
    $fileName = Split-Path $src -Leaf
    $dst = Join-Path $StateDir $fileName
    if ((Test-Path $src) -and -not (Test-Path $dst)) {
        Move-Item -Path $src -Destination $dst -Force
        Write-Host "[harness]   Migrated: $src -> $dst"
        $migrationDone = $true
    }
}

if ($migrationDone) {
    Write-Host "[harness]   Old state files migrated to $StateDir"
}

# === 9. 不复制任何文件到项目，不修改项目 CLAUDE.md ===
# 本脚本只创建 .claude\harness-cc\ 目录和配置文件

# === 10. 完成 ===
Write-Progress -Activity "harness-cc Setup" -Status "Done" -PercentComplete 100

$elapsed = [DateTime](Get-Date) - [DateTime]$startTime
Write-Host ""
Write-Host "============================================"
Write-Host "  harness-cc Setup Complete"
Write-Host "  Project type: $projectType"
Write-Host "  State dir: $StateDir"
Write-Host "  Elapsed: $($elapsed.TotalSeconds.ToString('0.0'))s"
Write-Host "============================================"
Write-Host ""
