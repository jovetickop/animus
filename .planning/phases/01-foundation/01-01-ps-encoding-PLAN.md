---
phase: "01-foundation"
plan: "01"
type: "execute"
wave: 1
depends_on: []
files_modified:
  - ".claude/templates/harness/update-progress.ps1"
  - ".claude/templates/harness/run-regression.ps1"
  - ".claude/templates/harness/coding-session.ps1"
  - ".claude/templates/harness/init.ps1"
  - ".claude/commands/check-consistency.ps1"
  - ".claude/commands/harness-code-setup.ps1"
  - ".claude/commands/validate-features.ps1"
autonomous: true
requirements:
  - "TECHD-01"
  - "TECHD-03"
must_haves:
  truths:
    - "所有 7 个 .ps1 文件编码为 UTF-8 with BOM，file 命令显示 utf-8"
    - "update-progress.ps1 第 100-112 行中文注释正常显示（通过/失败/进行中等）"
    - "git diff 可正确显示文本变更而非 binary files differ"
  artifacts:
    - path: ".claude/templates/harness/update-progress.ps1"
      provides: "状态机核心脚本（UTF-8 with BOM）"
      min_lines: 420
    - path: ".claude/templates/harness/run-regression.ps1"
      provides: "回归测试脚本（UTF-8 with BOM）"
    - path: ".claude/templates/harness/coding-session.ps1"
      provides: "编码会话脚本（UTF-8 with BOM）"
    - path: ".claude/templates/harness/init.ps1"
      provides: "初始化脚本（UTF-8 with BOM）"
    - path: ".claude/commands/check-consistency.ps1"
      provides: "一致性检查命令（UTF-8 with BOM）"
    - path: ".claude/commands/harness-code-setup.ps1"
      provides: "Setup 命令（UTF-8 with BOM）"
    - path: ".claude/commands/validate-features.ps1"
      provides: "特性验证命令（UTF-8 with BOM）"
  key_links:
    - from: ".claude/templates/harness/update-progress.ps1"
      to: ".claude/state/features.json"
      via: "路径查找逻辑"
      pattern: "features\\.json.*state"
---

<objective>
将 7 个 UTF-16LE 编码的 PowerShell 脚本转换为 UTF-8 with BOM，同时修复损坏的中文注释。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-foundation/01-RESEARCH.md
@.planning/codebase/CONCERNS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: 批量转换 7 个 UTF-16LE .ps1 文件为 UTF-8 with BOM</name>
  <files>.claude/templates/harness/update-progress.ps1, .claude/templates/harness/run-regression.ps1, .claude/templates/harness/coding-session.ps1, .claude/templates/harness/init.ps1, .claude/commands/check-consistency.ps1, .claude/commands/harness-code-setup.ps1, .claude/commands/validate-features.ps1</files>
  <read_first>
.claude/templates/harness/update-progress.ps1
.claude/commands/harness-code-setup.ps1
  </read_first>
  <action>
使用 PowerShell 原生命令进行编码转换（不依赖 iconv 等外部工具）：

```powershell
# 批量转换 UTF-16LE -> UTF-8 with BOM
Get-ChildItem -Recurse *.ps1 | Where-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE  # UTF-16LE BOM check
} | ForEach-Object {
    $content = Get-Content -Path $_.FullName -Raw
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8 -NoNewline
    Write-Host "Converted: $($_.FullName)"
}
```

转换顺序：
1. templates/harness/update-progress.ps1（最大文件，424行）
2. templates/harness/run-regression.ps1
3. templates/harness/coding-session.ps1
4. templates/harness/init.ps1
5. commands/check-consistency.ps1
6. commands/harness-code-setup.ps1
7. commands/validate-features.ps1
  </action>
  <acceptance_criteria>
- file --mime-encoding 对每个文件输出 "utf-8" 或 "UTF-8 Unicode (with BOM)"
- xxd -l 3 update-progress.ps1 输出前 3 字节为 "efbbbf"
- 所有 7 个文件转换后中文注释仍保留（无截断、无乱码增加）
  </acceptance_criteria>
  <verify>
<automated>
for f in .claude/templates/harness/*.ps1 .claude/commands/*.ps1; do encoding=$(file --mime-encoding "$f" 2>/dev/null | awk '{print $2}'); bom=$(xxd -l 3 "$f" 2>/dev/null | awk '{print $2}'); echo "$f: $encoding / BOM: $bom"; done
</automated>
  </verify>
  <done>7 个 .ps1 文件全部为 UTF-8 with BOM 编码，BOM 字节验证通过</done>
</task>

<task type="auto">
  <name>Task 2: 验证 update-progress.ps1 中文注释恢复情况</name>
  <files>.claude/templates/harness/update-progress.ps1</files>
  <read_first>.claude/templates/harness/update-progress.ps1</read_first>
  <action>
转换完成后，读取 update-progress.ps1 第 100-112 行（状态摘要 switch 语句），确认以下中文字符串正常显示：

损坏对照表：
- "�����Ǐ" → "通过"
- "����1Y%" → "失败"
- "ۏL�-N��_���� �" → "进行中"
- "�f�e�N�R�S�S��U_" → "首次执行"

使用 Select-String 搜索中文字符串验证：
```powershell
Select-String -Path .claude/templates/harness/update-progress.ps1 -Pattern "通过|失败|进行中|首次执行" | Select-Object -First 5
```

如仍有少量乱码，从上下文英文注释推断并手动修复对应行。
  </action>
  <acceptance_criteria>
- Select-String 能匹配到 "通过"、"失败"、"进行中"、"首次执行" 等中文字符串
- 无新增乱码（与转换前相比不增加乱码字符数）
  </acceptance_criteria>
  <verify>
<automated>
powershell -NoProfile -Command "Select-String -Path '.claude/templates/harness/update-progress.ps1' -Pattern '通过|失败|进行中|首次执行' | Select-Object -First 5"
</automated>
  </verify>
  <done>中文注释恢复正常显示，无乱码残留</done>
</task>

</tasks>

<verification>
## Phase 1 Wave 1 验证命令

### 编码验证
```bash
for f in .claude/templates/harness/*.ps1 .claude/commands/*.ps1; do
    encoding=$(file --mime-encoding "$f" 2>/dev/null | awk '{print $2}')
    bom=$(xxd -l 3 "$f" 2>/dev/null | awk '{print $2}')
    echo "$f: $encoding / BOM: $bom"
done
```
所有文件应显示 utf-8 编码，BOM 应为 efbbbf。

### 中文注释验证
```powershell
Select-String -Path .claude/templates/harness/update-progress.ps1 -Pattern "通过|失败|进行中|首次执行" | Select-Object -First 5
```
应输出包含中文的行。
</verification>

<success_criteria>
- 7 个 .ps1 文件全部为 UTF-8 with BOM
- BOM 字节验证 efbbbf 通过
- 中文注释正常显示
</success_criteria>

<output>
创建 .planning/phases/01-foundation/01-01-SUMMARY.md
</output>