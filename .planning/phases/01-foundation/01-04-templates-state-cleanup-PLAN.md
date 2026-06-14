---
phase: "01-foundation"
plan: "04"
type: "execute"
wave: 2
depends_on:
  - "01-03"
  - "01-01"
files_modified:
  - ".claude/templates/harness/features.json"
  - ".claude/templates/state/features.json"
  - ".claude/templates/state/features.active.json"
  - ".claude/templates/state/features.archive.json"
  - ".claude/templates/state/claude-progress.txt"
  - ".claude/templates/init-project.ps1"
autonomous: true
requirements:
  - "TECHD-05"
must_haves:
  truths:
    - "templates/harness/features.json 存在且为正确模板"
    - "templates/state/ 仅保留 features.json（备份）和 claude-progress.txt"
    - "init-project.ps1 从正确位置复制 features.json"
  artifacts:
    - path: ".claude/templates/harness/features.json"
      provides: "features.json 安装模板（合并自 features.active.json）"
    - path: ".claude/templates/state/features.json"
      provides: "features.json 备份（保留在 state/ 目录）"
    - path: ".claude/templates/state/claude-progress.txt"
      provides: "进度日志模板（保留在 state/ 目录）"
    - path: ".claude/templates/init-project.ps1"
      provides: "安装脚本（修复 source path bug）"
  key_links:
    - from: ".claude/templates/init-project.ps1"
      to: ".claude/templates/harness/features.json"
      via: "Copy-Item 命令"
      pattern: "features\\.json"
---

<objective>
清理 templates/state/ 目录，明确 JSON 模板角色，修复 init-project.ps1 的 source path bug。
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
  <name>Task 1: 修复 init-project.ps1 source path bug 并清理 templates/state/</name>
  <files>.claude/templates/init-project.ps1, .claude/templates/state/features.json, .claude/templates/state/features.active.json, .claude/templates/state/features.archive.json, .claude/templates/state/claude-progress.txt</files>
  <read_first>
.claude/templates/init-project.ps1
.claude/templates/state/features.json
.claude/templates/state/features.active.json
.claude/templates/state/features.archive.json
  </read_first>
  <action>
根据 RESEARCH.md Q5 分析，init-project.ps1 第 149 行期望 features.json 在 templates/harness/ 但该文件实际在 templates/state/。这是已确认的 bug。

**修复步骤：**

1. 将 features.active.json 的内容合并到 templates/harness/features.json（features.active.json 有 verify_config + tasks 含 parallel_group，是更完整的模板）

2. 删除 templates/state/features.active.json（已合并）

3. 删除 templates/state/features.archive.json（空 tasks 数组，无用途）

4. 保留 templates/state/features.json 作为备份（不在此处删除）

5. 保留 templates/state/claude-progress.txt（安装时复制到目标项目）

6. 修复 init-project.ps1 中的 source path：
   - 旧（错误）：查找 templates/state/features.json 或 templates/harness/features.json
   - 新（正确）：明确从 templates/harness/features.json 复制

**目录结构修复后：**
```
templates/
├── harness/          # init-project.ps1 从这里复制
│   ├── features.json # 合并后的完整模板
│   ├── update-progress.ps1
│   └── ...
└── state/            # 仅保留运行时状态文件
    ├── features.json # 备份（保留）
    └── claude-progress.txt
```
  </action>
  <acceptance_criteria>
- templates/harness/features.json 存在且包含完整的 tasks 数组和 verify_config
- templates/state/ 目录包含 features.json（备份）和 claude-progress.txt
- templates/state/features.active.json 和 features.archive.json 已删除
- init-project.ps1 中无 "源文件不存在: features.json" 警告
  </acceptance_criteria>
  <verify>
<automated>
echo "=== templates/harness/features.json 存在性 ===" && ls -la .claude/templates/harness/features.json 2>/dev/null && echo "=== templates/state/ 目录内容 ===" && ls -la .claude/templates/state/ && echo "=== features.json 有效性 ===" && python -m json.tool .claude/templates/harness/features.json > /dev/null && echo "JSON 有效"
</automated>
  </verify>
  <done>templates/state/ 清理完成，init-project.ps1 source path bug 修复</done>
</task>

</tasks>

<verification>
## Phase 1 Wave 2 模板清理验证

```bash
# 验证 templates/harness/features.json 存在且有效
python -m json.tool .claude/templates/harness/features.json > /dev/null && echo "JSON 有效"

# 验证 templates/state/ 包含 features.json 和 claude-progress.txt
ls .claude/templates/state/

# 验证 init-project.ps1 不再查找错误路径
git grep "templates/state/features.json" -- ".claude/templates/init-project.ps1" | grep -v "#" | grep -v "Write-Warning"
```
</verification>

<success_criteria>
- templates/harness/features.json 为有效 JSON 且包含完整模板
- templates/state/ 包含 features.json（备份）和 claude-progress.txt
- templates/state/features.active.json 和 features.archive.json 已删除
- init-project.ps1 从正确位置复制
</success_criteria>

<output>
创建 .planning/phases/01-foundation/01-04-SUMMARY.md
</output>