# 项目上下文

当前项目以 `CodeHarness` 的长任务工作流插件模式运行。复杂任务请先准备 PRD + 方案文档，再执行 `/code-plan` 拆解任务；简单任务可直接执行 `/code-plan`。

## 自动识别命令（/code-setup 回填）

- 项目类型：`{project-type}`
- 配置命令：`{配置命令}`
- 构建命令：`{构建命令}`
- 测试命令：`{测试命令}`
- 运行命令：`{运行命令}`

## 会话初始化（所有项目通用）

每次编码会话开始前执行：

```
.\.claude\harness\coding-session.ps1
python .claude/harness/show-status.py
Get-Content .claude/harness/claude-progress.txt -Tail 20 -Encoding UTF8
```

## 任务选择与状态流转（所有项目通用）

- 优先继续 in_progress 任务
- 状态仅允许：pending | in_progress | passed | failed
- 开始任务：`.\.claude\harness\update-progress.ps1 <TaskId> in_progress "说明"`
- 完成任务：`.\.claude\harness\update-progress.ps1 <TaskId> passed "完成说明"`

## 开发与验收（所有项目通用）

- 以 features.json 中的 acceptance_criteria 和 test_command 为准
- 至少执行构建和测试验证
- 没有构建/测试证据时，不得宣称任务完成

## 项目专项说明

{仅当 project-type = cpp-qt 时写入 Qt 专项验收要求}

## Git 提交

- 每个任务完成并通过验收后提交
- 按 .claude/rules/git-workflow.md 执行

## 必须长期维护的文件

- .claude/harness/features.json
- .claude/harness/claude-progress.txt
