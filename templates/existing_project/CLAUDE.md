# 项目上下文

当前项目以 `harness-cc` 的长任务工作流插件模式运行。技能安装目录 `${CLAUDE_PLUGIN_ROOT}`（Claude Code 自动设置）。

> **路径约定**：`${CLAUDE_PLUGIN_ROOT}` = 技能安装根目录（Claude Code 自动设置）。
> 目标项目运行时状态文件在 `.claude/harness-cc/` 目录中。

## 自动识别命令（/harness-code-setup 回填）

- 项目类型：`{project-type}` — 由 /harness-code-setup 初始化时填入
- 构建命令：`{构建命令}` — 由 /harness-code-setup 初始化时填入
- 测试命令：`{测试命令}` — 由 /harness-code-setup 初始化时填入
- 运行命令：`{运行命令}` — 由 /harness-code-setup 初始化时填入

## 会话初始化（MUST）

每次编码会话开始前，执行：

```powershell
& "${CLAUDE_PLUGIN_ROOT}\templates\harness\coding-session.ps1"
python "${CLAUDE_PLUGIN_ROOT}/templates/harness/show-status.py" .claude/harness-cc
python "${CLAUDE_PLUGIN_ROOT}/scripts/format-log.py" --project-dir . --recent 20
```

## 任务选择与状态流转（MUST）

- 优先继续 `in_progress` 任务。
- 若无 `in_progress`，选择依赖已满足且优先级最高的 `pending` 任务。
- 开始任务：`& "${CLAUDE_PLUGIN_ROOT}\templates\harness\update-progress.ps1" <TaskId> in_progress "说明"`
- 完成任务：`& "${CLAUDE_PLUGIN_ROOT}\templates\harness\update-progress.ps1" <TaskId> passed "完成说明"`
- 任务受阻：`& "${CLAUDE_PLUGIN_ROOT}\templates\harness\update-progress.ps1" <TaskId> failed "失败原因与下一步"`

状态仅允许：`pending | in_progress | passed | failed`。
- `.claude/harness-cc/features.json` 任务字段需包含：`depends_on`、`priority`、`last_error`、`updated_at`（后两项由 `update-progress.ps1` 自动维护）。

## 开发与验收（MUST）

- 以 `.claude/harness-cc/features.json` 中的 `acceptance_criteria` 和 `test_command` 为准。
- 至少执行构建和测试验证。
- 没有构建/测试证据时，不得宣称任务完成。

## 项目专项说明

{cpp-qt-specific} — 由 /harness-code-setup 在项目类型为 cpp-qt 时自动填入 Qt 专项验收要求

## Git 提交

- 每个任务完成并通过验收后，按 `${CLAUDE_PLUGIN_ROOT}/rules/universal/git-workflow.md` 执行提交。
- 提交信息格式：`<type>: <description>`，例如 `feat: 完成主窗口菜单行为`。
- 如果当前目录不是 Git 仓库，可跳过提交，但必须在 `.claude/harness-cc/harness-history.jsonl` 记录原因。

## 核心节奏

- 每轮只推进一个任务
- 每个任务结束都要构建和测试
- 每次结果都追加到 `.claude/harness-cc/harness-history.jsonl`
- 每次状态流转后自动更新 `.claude/harness-cc/docs/reports/<任务编号>-任务描述.md`

## 必须长期维护的文件

- `.claude/harness-cc/features.json`
- `.claude/harness-cc/harness-history.jsonl`
- `.claude/harness-cc/task_plan.md`
- `.claude/harness-cc/findings.md`
- `.claude/harness-cc/docs/reports/`

## 需要人工补充的项目特有信息

- 禁止修改的目录
- 项目架构约束

<!-- harness-cc -->
<!-- /harness-cc -->