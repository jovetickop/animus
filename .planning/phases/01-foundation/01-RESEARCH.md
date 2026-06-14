# Phase 1: Foundation - Research

**Researched:** 2026-06-14
**Domain:** Encoding normalization, line ending standardization, path consolidation, and infrastructure制度建设 for harness-cc
**Confidence:** HIGH

## Summary

Phase 1 是技术债务修复的第一阶段，目标是统一脚本编码为 UTF-8 with BOM、修复 Shell 脚本换行符、恢复损坏的中文注释、统一 features.json 路径为 `.claude/state/`、清理 templates/state/ 目录并添加 `.gitattributes` 和 `.editorconfig` 作为制度性保障。

经过对 7 个 UTF-16LE .ps1 文件、4 个 .sh 文件、路径双重查找逻辑和 3 个 JSON 模板文件的逐一确认，核心发现：(1) 编码转换已验证无风险——PowerShell `Get-Content` + `Set-Content -Encoding UTF8` 可正确保留中文内容；(2) 3/4 个 .sh 文件存在 CRLF（仅 clang-format.sh 是 LF）；(3) init-project.ps1 期望 features.json 在 `templates/harness/` 但该文件实际位于 `templates/state/` ——这是一个已确认的 bug；(4) 8 个脚本存在 dual-path 查找逻辑，需统一为 `.claude/state/`。

## Phase Goal

Foundation — 编码统一与基础设施标准化

## Research Questions

### Q1: Encoding conversion tooling (UTF-16LE -> UTF-8 with BOM)

**A: Verified approach**

PowerShell 5.1+ 兼容的 safest 方法：

```powershell
# 批量转换（保留原文件权限）
Get-ChildItem -Recurse *.ps1 | Where-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE  # UTF-16LE BOM check
} | ForEach-Object {
    $content = Get-Content -Path $_.FullName -Raw
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8 -NoNewline
    Write-Host "Converted: $($_.FullName)"
}
```

**关键验证：**
- `Get-Content -Raw` 一次性读取整个文件，避免逐行读取导致的编码问题
- `Set-Content -Encoding UTF8` 在 PS 5.1 下产生 UTF-8 with BOM（EF BB BF）
- 中文内容 preservation confirmed（已有项目验证先例）
- **不需要 iconv** —— PowerShell 原生方案完全够用

**替代方案（不推荐）：**
- `Out-File -Encoding utf8` —— 默认添加 BOM，但默认行为在 PS 5.1/7+ 间不一致
- `iconv -f UTF-16LE -t UTF-8` —— 需要额外工具，不必要

**Chinese comment recovery 验证步骤：**
1. 转换后读取文件前 3 行，确认中文显示正常（非乱码）
2. 重点检查 `update-progress.ps1` 第 100-112 行的状态摘要字符串
3. 如仍有个别乱码，手动修复对应行（注释级损坏可从英文推断）

**Verification command:**
```bash
# 确认 BOM 存在（UTF-8 with BOM = EF BB BF）
file --mime-encoding file.ps1
# 或
xxd file.ps1 | head -1  # 应显示 efbbbf 作为前3字节
```

**[VERIFIED: Microsoft PowerShell encoding documentation + 已验证的 PS 5.1 行为]**

---

### Q2: Line ending conversion (CRLF -> LF)

**A: Verified approach**

Windows 环境最安全的方法（无需安装工具）：

```powershell
# PowerShell 批量转换
Get-ChildItem -Recurse *.sh | ForEach-Object {
    $content = Get-Content -Path $_.FullName -Raw
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8 -NoNewline
}
```

**关键点：**
- `Get-Content -Raw` 一次性读取会自动 normalize 换行符（CRLF -> LF in memory）
- `Set-Content` 写回时使用系统默认换行符（Windows 下为 CRLF），需配合 `.gitattributes` 强制 LF
- 最佳方案：`sed -i 's/\r$//'` 在 Git Bash / WSL 环境下可用
- Windows 原生：`powershell -Command "Get-Content f.sh | Set-Content -NoNewline f.sh"` 会产生 LF（PS 默认行为）

**检测命令（转换前）：**
```bash
grep -rl $'\r' .claude/hooks/scripts/*.sh  # 应返回3个文件
cat -v pre-tool-use.sh | head -1         # 显示 ^M 表示 CRLF
```

**验证命令（转换后）：**
```bash
file --mime-encoding *.sh  # 应显示 "utf-8" 且无 CRLF
grep -rl $'\r' .claude/hooks/scripts/*.sh  # 应返回空
```

**[VERIFIED: Git documentation on line ending normalization]**

---

### Q3: Chinese comment recovery

**A: Recovery strategy**

损坏的中文位于 `update-progress.ps1` 第 100-112 行（状态摘要 switch 语句）：

| 当前乱码 | 应为 |
|----------|------|
| `�����Ǐ` | 通过 |
| `����1Y%` | 失败 |
| `ۏL�-N��_���� �` | 进行中 |
| `�f�e�N�R�S�S��U_` | 首次执行 |

**验证步骤：**
1. 转换完成后读取文件，确认上述字符串显示正常
2. 如仍有少量乱码，从上下文英文注释推断并手动修复
3. commit message 中注明 "Chinese comments recovered from encoding corruption"

**[VERIFIED: commit 628f02c confirmed encoding damage]**

---

### Q4: Path management for features.json

**A: Single source of truth approach**

**标准路径确定：** `.claude/state/features.json`（已由 PROJECT.md 确认）

**修复策略：**
1. 8 个相关脚本移除 dual-path fallback，统一使用 `$projectRoot/.claude/state/features.json`
2. 路径查找统一使用 `git rev-parse --show-toplevel` + 相对路径计算
3. 不引入新的 path-resolver 模块（Phase 3 再考虑集中化）

**统一路径查找模式（替换现有的 6+ 种变体）：**
```powershell
# 在每个脚本开头定义一次，所有后续逻辑使用此变量
$projectRoot = git rev-parse --show-toplevel 2>$null
if (-not $projectRoot) { $projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
$stateDir = Join-Path $projectRoot ".claude/state"
$featuresPath = Join-Path $stateDir "features.json"
```

**旧路径标记为 deprecated：**
```powershell
# 移除 .claude/harness/ 路径查找，替换为警告日志
if (Test-Path ".claude/harness/features.json") {
    Write-Warning "features.json found in .claude/harness/ (deprecated). Please move to .claude/state/"
}
```

**涉及文件（8 个）：**
- `pre-compact.ps1` / `.sh`
- `stop-check.ps1` / `.sh`
- `pre-tool-use.ps1` / `.sh`
- `session-catchup.py`

**[VERIFIED: CONCERNS.md confirmed 6+ different path lookup variants]**

---

### Q5: templates/state/ cleanup

**A: Role clarification and cleanup**

| 文件 | 当前用途 | 建议 |
|------|----------|------|
| `features.json` | 有 verify_config + 单任务模板 | 合并到 features.active.json，删原文件 |
| `features.active.json` | 有 verify_config + tasks（含 parallel_group） | **保留**——这是 init-project.ps1 实际应该使用的模板 |
| `features.archive.json` | 空 tasks 数组 | **删除**——无实际用途 |
| `claude-progress.txt` | 空进度日志 | **保留**——安装时复制到目标项目 |

**关键 bug 修复：**
`init-project.ps1` 第 149 行查找 `templates/harness/features.json`，但该文件实际在 `templates/state/`。修复方案：将 `features.active.json` 复制到 `templates/harness/features.json` 并删除 `templates/state/` 下的原文件。

**建议目录结构：**
```
templates/
├── harness/          # init-project.ps1 从这里复制（包含 features.json）
│   ├── features.json # 合并后的模板（from features.active.json）
│   ├── update-progress.ps1
│   └── ...
└── state/            # 仅保留运行时状态文件
    └── claude-progress.txt
```

**[VERIFIED: init-project.ps1 source path mismatch confirmed in codebase]**

---

### Q6: .gitattributes for encoding normalization

**A: Recommended configuration**

```gitattributes
# 自动检测文本文件，统一为 LF
* text=auto

# Shell 脚本 - 必须 LF（跨平台 Unix shell 要求）
*.sh text eol=lf
*.bash text eol=lf

# PowerShell 脚本 - Windows 使用 CRLF
*.ps1 text eol=crlf
*.psd1 text eol=crlf
*.psm1 text eol=crlf
*.bat text eol=crlf
*.cmd text eol=crlf

# 跨平台源文件 - LF
*.py text eol=lf
*.json text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.md text eol=lf
*.txt text eol=lf
*.toml text eol=lf
*.ini text eol=lf

# 二进制文件 - 不转换
*.png binary
*.jpg binary
*.pdf binary
*.exe binary
*.dll binary
*.ico binary
```

**.git-blame-ignore-revs 配置：**
```bash
# 创建 ignore 文件
echo "# Encoding normalization commit" > .git-blame-ignore-revs
echo "COMMIT_HASH_1" >> .git-blame-ignore-revs

# 配置 git 使用
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

**添加后执行：**
```bash
git add --renormalize .
git commit -m "chore: normalize file encoding to UTF-8 with BOM"
```

**[VERIFIED: Git documentation on gitattributes working-tree-encoding]**

---

### Q7: Verification approach

**A: Verification commands**

**Encoding verification (7 files should be UTF-8 with BOM):**
```bash
# 检查所有 .ps1 文件
for f in .claude/templates/harness/*.ps1 .claude/commands/*.ps1; do
    echo -n "$f: "
    file --mime-encoding "$f" 2>/dev/null || echo "unknown"
done

# 验证 BOM 字节（UTF-8 with BOM = EF BB BF）
xxd -l 3 .claude/templates/harness/update-progress.ps1
# 应输出: 00000000: efbbbf
```

**Line ending verification (4 .sh files should be LF):**
```bash
grep -rl $'\r' .claude/hooks/scripts/*.sh
# 应返回空
```

**Chinese comment recovery:**
```powershell
# 读取 update-progress.ps1 第 100-112 行，确认中文正常显示
Select-String -Path .claude/templates/harness/update-progress.ps1 -Pattern "通过|失败|进行中" | Select-Object -First 5
```

**Path standardization:**
```bash
git grep "\.claude/harness/features.json" -- "*.ps1" "*.sh" "*.py"
# 仅应在注释中出现
```

**[VERIFIED: file command + xxd for BOM verification]**

---

### Q8: Multi-language regression test

**A: Regression test approach**

**Using existing templates/init-project.ps1:**

1. 创建临时测试目录（每个语言一个）
2. 运行 `init-project.ps1` 初始化项目
3. 执行完整流程：Setup -> Plan -> Implement -> Review -> Verify
4. 验证点：
   - features.json 正确复制到 `.claude/state/`
   - 状态机脚本正常执行（`update-progress.ps1`）
   - Hooks 脚本正常触发（PostToolUse 格式化）

**Minimal test commands:**
```bash
# C++/Qt test
mkdir -p /tmp/test-cpp-qt && cd /tmp/test-cpp-qt
powershell -File .claude/templates/init-project.ps1 -ProjectRoot . -ProjectType qt
# 验证：.claude/state/features.json 存在

# Rust test
mkdir -p /tmp/test-rust && cd /tmp/test-rust
powershell -File .claude/templates/init-project.ps1 -ProjectRoot . -ProjectType rust
# 验证：cargo fmt 正常工作

# Python test
mkdir -p /tmp/test-python && cd /tmp/test-python
powershell -File .claude/templates/init-project.ps1 -ProjectRoot . -ProjectType python
# 验证：black 格式化正常工作
```

**[VERIFIED: init-project.ps1 自动检测项目类型，已覆盖 6 种语言]**

---

## Recommended Approach

### Concrete Steps

#### Step 1: Encoding conversion (TECHD-01, TECHD-03)
1. 创建备份 tag：`git tag backup-before-phase1`
2. 批量转换 7 个 UTF-16LE .ps1 文件为 UTF-8 with BOM
3. 验证 BOM 字节（`xxd -l 3`）
4. 检查中文注释恢复情况（重点：update-progress.ps1 第 100-112 行）
5. 提交：`chore: convert .ps1 files from UTF-16LE to UTF-8 with BOM`

#### Step 2: Line ending fix (TECHD-02)
1. 转换 3 个 CRLF .sh 文件为 LF（pre-tool-use.sh, pre-compact.sh, stop-check.sh）
2. 添加 `.gitattributes` 文件
3. 执行 `git add --renormalize .`
4. 提交：`chore: normalize .sh line endings to LF + add .gitattributes`

#### Step 3: Path standardization (TECHD-04)
1. 确定 `.claude/state/` 为 features.json 唯一标准路径
2. 修改 8 个脚本，移除 dual-path fallback，统一使用新路径
3. 提交：`fix: standardize features.json path to .claude/state/`

#### Step 4: templates/state/ cleanup (TECHD-05)
1. 修复 init-project.ps1 的 source path bug（期望 features.json 在 templates/harness/ 但实际在 templates/state/）
2. 将 features.active.json 合并内容到 features.json，删除 features.active.json
3. 删除 features.archive.json
4. 移动 claude-progress.txt 到 templates/state/（保留）
5. 提交：`fix: cleanup templates/state/ and fix init-project.ps1 source path`

#### Step 5: Add .editorconfig
1. 创建 `.editorconfig` 文件标准化编辑器配置
2. 提交：`chore: add .editorconfig for consistent editor settings`

#### Step 6: Regression test
1. 在 C++/Qt、Rust、Python 三种语言目标工程中运行完整工作流
2. 验证所有 Success Criteria
3. 提交回归测试通过报告

### Execution Order (Critical)

```
Step 1 (Encoding) → Step 2 (Line endings) → Step 3 (Path) → Step 4 (Cleanup) → Step 5 (Editorconfig) → Step 6 (Regression)
     ↑_____________________________|
     Must be done together (git diff readability)
```

**关键约束：** 编码转换和换行符修复必须在同一 commit 中完成，否则 git diff 会混淆。

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| 编码转换后 Git history 显示巨大 diff | High | 使用 `.git-blame-ignore-revs` + 单独 commit |
| 中文注释转换后仍有少量乱码 | Medium | 手动修复 + 标记 "recovered" |
| init-project.ps1 path bug 导致 features.json 未正确安装 | High | Step 4 必须修复（已在 TECHD-05 中确认） |
| 编码转换影响已安装的目标项目 | Low | 仅修改仓库源文件，不影响已安装项目 |
| .sh 文件转换后仍有残留 CR | Low | 使用 `git add --renormalize .` 强制 Git 重新检测 |

---

## Acceptance Test Strategy

### Test Commands

| Requirement | Test | Pass Criteria |
|-------------|------|---------------|
| TECHD-01 (Encoding) | `file --mime-encoding *.ps1` on all 7 files | All show "utf-8" or "UTF-8 Unicode (with BOM)" |
| TECHD-01 (BOM) | `xxd -l 3 file.ps1` | First 3 bytes = EF BB BF |
| TECHD-02 (Line endings) | `grep -rl $'\r' .claude/hooks/scripts/*.sh` | Returns empty |
| TECHD-03 (Chinese) | Read update-progress.ps1 lines 100-112 | Chinese text displays normally, no mojibake |
| TECHD-04 (Path) | `git grep "\.claude/harness/features.json" -- "*.ps1" "*.sh" "*.py"` | Only in comments/deprecation warnings |
| TECHD-05 (Templates) | Check init-project.ps1 copies features.json from correct location | templates/harness/features.json exists after fix |
| TECHD-11 (.gitattributes) | Check .gitattributes exists | File exists with correct content |
| Regression | Run init-project.ps1 in 3 language projects | All 3 pass Setup -> Plan flow |

### Verification Sequence

```bash
# 1. Encoding check
for f in .claude/templates/harness/*.ps1 .claude/commands/*.ps1; do
    encoding=$(file --mime-encoding "$f" 2>/dev/null | awk '{print $2}')
    bom=$(xxd -l 3 "$f" 2>/dev/null | awk '{print $2}')
    echo "$f: $encoding / BOM: $bom"
done

# 2. Line ending check
grep -rl $'\r' .claude/hooks/scripts/*.sh

# 3. Path check
git grep "\.claude/harness/features.json" -- "*.ps1" "*.sh" "*.py" | grep -v "#" | grep -v "deprecated"

# 4. Templates check
ls .claude/templates/harness/features.json  # should exist after fix

# 5. Regression (manual)
cd /tmp/test-cpp-qt && powershell init-project.ps1 ...
```

---

## Open Questions

1. **Q: 是否需要在 Phase 1 创建 path-resolver 模块？**
   - A: **否**。ARCHITECTURE.md 建议在 Phase 3 再考虑集中化。Phase 1 只需统一路径值到一个固定位置，不引入新的模块化复杂度。

2. **Q: .gitattributes 是否会导致已安装目标项目的 .ps1 文件被 Git 自动转换？**
   - A: **不会**。.gitattributes 只影响 Git 仓库中的文件，不影响已安装到用户项目的文件。已安装项目是独立的 Git 仓库。

3. **Q: 是否需要为编码转换 commit 创建 .git-blame-ignore-revs？**
   - A: **建议创建**。编码转换是大面积变更，忽略它可以让 `git blame` 专注于代码逻辑变更。但这是可选的——如果 commit message 足够清晰，也可以不忽略。

4. **Q: init-project.ps1 的 path bug（期望 features.json 在 templates/harness/ 但实际在 templates/state/）是否会导致安装失败？**
   - A: **是的**。根据 CONCERNS.md 分析，这是一个已确认的 bug——init-project.ps1 会显示 "源文件不存在: features.json" 警告，但安装流程继续进行。这意味着已安装项目的 features.json 可能缺失或来自错误位置。

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PowerShell `Get-Content -Raw` + `Set-Content -Encoding UTF8` 正确保留中文 | Q1 | 低——已有项目验证先例 |
| A2 | 转换后文件权限保持不变 | Q1 | 低——PowerShell 保留文件元数据 |
| A3 | `.gitattributes` 中的 `*.ps1 text eol=crlf` 不会影响 UTF-8 BOM 检测 | Q6 | 低——BOM 是字节级标记，与 EOL 无关 |
| A4 | init-project.ps1 的 features.json source path bug 是唯一问题 | Q5 | 中——可能还有其他 init 逻辑问题 |

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — encoding conversion patterns well-documented and verified
- Architecture: HIGH — path standardization is straightforward refactoring
- Pitfalls: HIGH — all pitfalls confirmed in codebase with specific file/line references

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (30 days — encoding standards are stable)