---
phase: "01-foundation"
plan: "02"
type: "execute"
wave: 1
depends_on: []
files_modified:
  - ".claude/hooks/scripts/pre-compact.sh"
  - ".claude/hooks/scripts/pre-tool-use.sh"
  - ".claude/hooks/scripts/stop-check.sh"
  - ".claude/hooks/scripts/clang-format.sh"
autonomous: true
requirements:
  - "TECHD-02"
must_haves:
  truths:
    - "所有 .sh 文件换行符为 LF（grep -rl $'\\r' 返回空）"
    - "Shell 脚本在 WSL/Linux/macOS 上可直接执行无 \"No such file or directory\" 报错"
  artifacts:
    - path: ".claude/hooks/scripts/pre-compact.sh"
      provides: "PreCompact Hook Shell 版（LF 换行符）"
    - path: ".claude/hooks/scripts/pre-tool-use.sh"
      provides: "PreToolUse Hook Shell 版（LF 换行符）"
    - path: ".claude/hooks/scripts/stop-check.sh"
      provides: "Stop Check Hook Shell 版（LF 换行符）"
    - path: ".claude/hooks/scripts/clang-format.sh"
      provides: "ClangFormat Hook Shell 版（LF 换行符）"
  key_links:
    - from: ".claude/hooks/scripts/"
      to: "hooks.json"
      via: "bash 降级路径"
      pattern: "bash.*\\.sh"
---

<objective>
修复 .sh 文件的换行符问题（CRLF → LF），确保跨平台兼容性。
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
  <name>Task 1: 转换 4 个 .sh 文件从 CRLF 到 LF</name>
  <files>.claude/hooks/scripts/pre-compact.sh, .claude/hooks/scripts/pre-tool-use.sh, .claude/hooks/scripts/stop-check.sh, .claude/hooks/scripts/clang-format.sh</files>
  <read_first>
.claude/hooks/scripts/pre-compact.sh
.claude/hooks/scripts/pre-tool-use.sh
  </read_first>
  <action>
使用 PowerShell 原生命令转换换行符（无需安装工具）：

```powershell
Get-ChildItem -Recurse *.sh | ForEach-Object {
    $content = Get-Content -Path $_.FullName -Raw
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8 -NoNewline
    Write-Host "Converted: $($_.FullName)"
}
```

注：Get-Content -Raw 一次性读取会自动 normalize 换行符（CRLF → LF in memory），Set-Content 写回时使用系统默认但配合后续的 .gitattributes 强制 LF。

或者在 Git Bash 环境下使用：
```bash
sed -i 's/\r$//' .claude/hooks/scripts/pre-compact.sh .claude/hooks/scripts/pre-tool-use.sh .claude/hooks/scripts/stop-check.sh .claude/hooks/scripts/clang-format.sh
```
  </action>
  <acceptance_criteria>
- grep -rl $'\r' .claude/hooks/scripts/*.sh 返回空
- cat -v 文件.sh | head -1 不显示 ^M
- file --mime-encoding 文件.sh 显示 utf-8
  </acceptance_criteria>
  <verify>
<automated>
grep -rl $'\r' .claude/hooks/scripts/*.sh
</automated>
  </verify>
  <done>所有 .sh 文件换行符为 LF，验证通过</done>
</task>

</tasks>

<verification>
## Phase 1 Wave 1 换行符验证

```bash
# 转换前检测（应返回 3 个文件）
grep -rl $'\r' .claude/hooks/scripts/*.sh

# 转换后验证（应返回空）
grep -rl $'\r' .claude/hooks/scripts/*.sh

# BOM 验证
for f in .claude/hooks/scripts/*.sh; do
    echo -n "$f: "
    xxd -l 3 "$f" | head -1
done
```
</verification>

<success_criteria>
- grep -rl $'\r' 返回空
- 所有 .sh 文件为 UTF-8 编码
</success_criteria>

<output>
创建 .planning/phases/01-foundation/01-02-SUMMARY.md
</output>