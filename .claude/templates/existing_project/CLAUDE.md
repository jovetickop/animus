# 项目上下文

当前项目以 `CodeHarness` 的长任务工作流插件模式运行。复杂任务请先准备 PRD + 方案文档，再执行 `/code-plan` 拆解任务；简单任务可直接执行 `/code-plan`。

## 自动识别命令（/code-setup 回填）

- 项目类型：`{project-type}`
- 配置命令：`{配置命令}`
- 构建命令：`{构建命令}`
- 测试命令：`{测试命令}`
- 运行命令：`{运行命令}`

要求：
- `/code-setup` 必须自动探测并回填以上命令。
- 若测试入口暂缺，写明探测失败原因，并给出最小 smoke test 补齐建议。

## 会话初始化（MUST）

每次编码会话开始前，执行：

```powershell
.\.claude\harness\coding-session.ps1
python .claude/harness/show-status.py
Get-Content .claude/harness/claude-progress.txt -Tail 20 -Encoding UTF8
```

若为全新环境，先执行一次：

```powershell
.\.claude\harness\init.ps1
```

## 任务选择与状态流转（MUST）

- 优先继续 `in_progress` 任务。
- 若无 `in_progress`，选择依赖已满足且优先级最高的 `pending` 任务。
- 开始任务：`.\.claude\harness\update-progress.ps1 <TaskId> in_progress "说明" [-AutoPush]`
- 完成任务：`.\.claude\harness\update-progress.ps1 <TaskId> passed "完成说明" [-AutoPush]`
- 任务受阻：`.\.claude\harness\update-progress.ps1 <TaskId> failed "失败原因与下一步" [-AutoPush]`
- 默认保持失败任务为 `failed`，重试时再切回 `in_progress`。
- 仅在人工确认需要重排任务时，才允许把 `failed` 改回 `pending`。

状态仅允许：`pending | in_progress | passed | failed`。
- `features.json` 任务字段需包含：`depends_on`、`priority`、`last_error`、`updated_at`（后两项由 `update-progress.ps1` 自动维护）。

## 开发与验收（MUST）

- 以 `.claude/harness/features.json` 中的 `acceptance_criteria` 和 `test_command` 为准。
- 至少执行构建和测试验证。
- 没有构建/测试证据时，不得宣称任务完成。

## 项目专项说明

{仅当 project-type = cpp-qt 时写入 Qt 专项验收要求}

## Git 提交

- 每个任务完成并通过验收后，按 `.claude/rules/git-workflow.md` 执行提交。
- 提交信息格式：`<type>: <description>`，例如 `feat: 完成主窗口菜单行为`。
- 如果当前目录不是 Git 仓库，可跳过提交，但必须在 `.claude/harness/claude-progress.txt` 记录原因。

## 核心节奏

- 每轮只推进一个任务
- 每个任务结束都要构建和测试
- 每次结果都写入 `.claude/harness/claude-progress.txt`
- 每次状态流转后自动更新 `docs/reports/<任务编号>-任务描述.md`

## 必须长期维护的文件

- `.claude/harness/features.json`
- `.claude/harness/claude-progress.txt`
- `docs/reports/`
- `.claude/rules/`

## 需要人工补充的项目特有信息

- 禁止修改的目录
- 项目架构约束
