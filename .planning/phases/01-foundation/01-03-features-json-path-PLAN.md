---
phase: "01-foundation"
plan: "03"
type: "execute"
wave: 2
depends_on:
  - "01-01"
files_modified:
  - ".claude/hooks/scripts/pre-compact.ps1"
  - ".claude/hooks/scripts/pre-tool-use.ps1"
  - ".claude/hooks/scripts/stop-check.ps1"
  - ".claude/hooks/scripts/clang-format.ps1"
  - ".claude/templates/harness/show-status.py"
  - ".claude/scripts/session-catchup.py"
  - ".claude/hooks/scripts/pre-compact.sh"
  - ".claude/hooks/scripts/pre-tool-use.sh"
autonomous: true
requirements:
  - "TECHD-04"
must_haves:
  truths:
    - "features.json 的唯一标准路径为 .claude/state/"
    - "8 个脚本中移除了对 .claude/harness/features.json 的双重查找逻辑"
    - "git grep 不再在代码逻辑中找到旧路径（仅允许在注释/deprecation 警告中出现）"
  artifacts:
    - path: ".claude/hooks/scripts/pre-compact.ps1"
      provides: "PreCompact Hook PS 版（统一路径查找）"
    - path: ".claude/hooks/scripts/pre-tool-use.ps1"
      provides: "PreToolUse Hook PS 版（统一路径查找）"
    - path: ".claude/hooks/scripts/stop-check.ps1"
      provides: "Stop Check Hook PS 版（统一路径查找）"
    - path: ".claude/hooks/scripts/clang-format.ps1"
      provides: "ClangFormat Hook PS 版（统一路径查找）"
    - path: ".claude/templates/harness/show-status.py"
      provides: "状态展示 Python 脚本（统一路径查找）"
    - path: ".claude/scripts/session-catchup.py"
      provides: "会话恢复 Python 脚本（统一路径查找）"
    - path: ".claude/hooks/scripts/pre-compact.sh"
      provides: "PreCompact Hook Shell 版（统一路径查找）"
    - path: ".claude/hooks/scripts/pre-tool-use.sh"
      provides: "PreToolUse Hook Shell 版（统一路径查找）"
  key_links:
    - from: "8 个脚本"
      to: ".claude/state/features.json"
      via: "统一路径查找逻辑"
      pattern: "\\.claude/state/features\\.json"
---

<objective>
统一 features.json 标准路径为 .claude/state/，消除 8 个脚本中的双重查找逻辑。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-foundation/01-RESEARCH.md
@.planning/research/ARCHITECTURE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: 修改 PowerShell 脚本统一路径查找逻辑</name>
  <files>.claude/hooks/scripts/pre-compact.ps1, .claude/hooks/scripts/pre-tool-use.ps1, .claude/hooks/scripts/stop-check.ps1, .claude/hooks/scripts/clang-format.ps1</files>
  <read_first>
.claude/hooks/scripts/pre-compact.ps1
.claude/hooks/scripts/pre-tool-use.ps1
.claude/hooks/scripts/stop-check.ps1
.claude/hooks/scripts/clang-format.ps1
  </read_first>
  <action>
在每个 PowerShell 脚本开头定义统一路径变量，替换现有的多种路径查找变体：

```powershell
# 统一路径查找（在脚本开头定义一次）
$projectRoot = git rev-parse --show-toplevel 2>$null
if (-not $projectRoot) { $projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
$stateDir = Join-Path $projectRoot ".claude/state"
$featuresPath = Join-Path $stateDir "features.json"
```

移除所有 dual-path fallback 逻辑（删除对 .claude/harness/features.json 的查找）。

如果旧路径存在，添加 deprecation 警告：
```powershell
if (Test-Path (Join-Path $projectRoot ".claude/harness/features.json")) {
    Write-Warning "features.json found in .claude/harness/ (deprecated). Please move to .claude/state/"
}
```

修改文件列表：
1. pre-compact.ps1 - 替换路径查找逻辑
2. pre-tool-use.ps1 - 替换路径查找逻辑
3. stop-check.ps1 - 替换路径查找逻辑
4. clang-format.ps1 - 替换路径查找逻辑
  </action>
  <acceptance_criteria>
- 所有脚本使用统一的 $featuresPath 变量指向 .claude/state/features.json
- 无 .claude/harness/features.json 的代码级引用（仅注释/deprecation 警告允许）
- git grep "\.claude/harness/features\.json" -- "*.ps1" "*.sh" "*.py" 仅返回注释或警告行
  </acceptance_criteria>
  <verify>
<automated>
git grep "\.claude/harness/features\.json" -- "*.ps1" "*.sh" "*.py" | grep -v "#" | grep -v "deprecated" | grep -v "Write-Warning"
</automated>
  </verify>
  <done>8 个脚本路径查找逻辑统一，无旧路径代码残留</done>
</task>

<task type="auto">
  <name>Task 2: 修改 Shell 脚本统一路径查找逻辑</name>
  <files>.claude/hooks/scripts/pre-compact.sh, .claude/hooks/scripts/pre-tool-use.sh</files>
  <read_first>
.claude/hooks/scripts/pre-compact.sh
.claude/hooks/scripts/pre-tool-use.sh
  </read_first>
  <action>
在每个 Shell 脚本中定义统一路径变量：

```bash
# 统一路径查找
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.claude/state"
FEATURES_PATH="$STATE_DIR/features.json"
```

移除所有 dual-path fallback 逻辑。

修改文件列表：
1. pre-compact.sh - 替换路径查找逻辑
2. pre-tool-use.sh - 替换路径查找逻辑

注：stop-check.sh 和 clang-format.sh 可能不直接引用 features.json（如需修改参照 pre-compact.sh 模式）。
  </action>
  <acceptance_criteria>
- 所有 Shell 脚本使用统一的 FEATURES_PATH 变量指向 .claude/state/features.json
- git grep "\.claude/harness/features\.json" -- "*.sh" 仅返回注释或警告行
  </acceptance_criteria>
  <verify>
<automated>
git grep "\.claude/harness/features\.json" -- "*.sh" | grep -v "#" | grep -v "deprecated"
</automated>
  </verify>
  <done>Shell 脚本路径查找逻辑统一</done>
</task>

<task type="auto">
  <name>Task 3: 修改 Python 脚本统一路径查找逻辑</name>
  <files>.claude/templates/harness/show-status.py, .claude/scripts/session-catchup.py</files>
  <read_first>
.claude/templates/harness/show-status.py
.claude/scripts/session-catchup.py
  </read_first>
  <action>
在 Python 脚本中定义统一路径函数（遵循 Python 2/3 兼容模式）：

```python
from __future__ import print_function
import os
import sys

def find_project_root(start_path=None):
    """从 start_path 向上遍历查找 .claude/state/ 目录"""
    if start_path is None:
        start_path = os.path.dirname(os.path.abspath(__file__))
    current = start_path
    for _ in range(10):  # 最多向上 10 层
        state_dir = os.path.join(current, '.claude', 'state')
        if os.path.isdir(state_dir):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None

def get_features_path(project_root=None):
    """返回标准的 features.json 路径"""
    if project_root is None:
        project_root = find_project_root()
    if project_root:
        return os.path.join(project_root, '.claude', 'state', 'features.json')
    return None
```

替换脚本中所有硬编码的 features.json 路径为 get_features_path() 调用。
  </action>
  <acceptance_criteria>
- Python 脚本使用统一的 get_features_path() 函数
- git grep "\.claude/harness/features\.json" -- "*.py" 仅返回注释或警告行
  </acceptance_criteria>
  <verify>
<automated>
git grep "\.claude/harness/features\.json" -- "*.py" | grep -v "#" | grep -v "deprecated"
</automated>
  </verify>
  <done>Python 脚本路径查找逻辑统一</done>
</task>

</tasks>

<verification>
## Phase 1 Wave 2 路径标准化验证

```bash
# 验证无旧路径代码残留
git grep "\.claude/harness/features\.json" -- "*.ps1" "*.sh" "*.py" | grep -v "#" | grep -v "deprecated" | grep -v "Write-Warning"

# 验证新路径存在
ls -la .claude/state/features.json 2>/dev/null || echo "文件不存在（将在后续步骤创建）"
```
</verification>

<success_criteria>
- 所有 8 个脚本使用统一路径 .claude/state/features.json
- 无旧路径代码残留
</success_criteria>

<output>
创建 .planning/phases/01-foundation/01-03-SUMMARY.md
</output>