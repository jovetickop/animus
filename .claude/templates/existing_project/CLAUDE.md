# 项目上下文

当前项目以 `ty-qt-ai-plugin` 的“已有工程接入模式”运行。

## 1. 自动识别命令（setup MUST 填写）

- 配置命令：`<AUTO_DETECTED_CONFIGURE_COMMAND>`
- 构建命令：`<AUTO_DETECTED_BUILD_COMMAND>`
- 测试命令：`<AUTO_DETECTED_TEST_COMMAND>`
- 运行命令：`<AUTO_DETECTED_RUN_COMMAND>`

要求：

- `setup` 必须自动探测并回填，不要把占位符留给人工处理。
- 若测试入口暂缺，写明探测失败原因，并给出最小 smoke test 补齐建议。

## 2. 会话初始化（MUST）

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

## 3. 任务选择与状态流转（MUST）

- 优先继续 `in_progress` 任务。
- 若无 `in_progress`，选择依赖已满足且优先级最高的 `pending` 任务。
- 开始任务：
  `.\.claude\harness\update-progress.ps1 <TaskId> in_progress "开始实现..." [-AutoPush]`
- 完成任务：
  `.\.claude\harness\update-progress.ps1 <TaskId> passed "完成说明" [-AutoPush]`
- 任务受阻：
  `.\.claude\harness\update-progress.ps1 <TaskId> failed "失败原因与下一步" [-AutoPush]`
- 默认保持失败任务为 `failed`，重试时再切回 `in_progress`。
- 仅在人工确认需要重排任务时，才允许把 `failed` 改回 `pending`。

状态仅允许：`pending | in_progress | passed | failed`。
- `features.json` 任务字段需包含：`depends_on`、`priority`、`last_error`、`updated_at`（后两项由 `update-progress.ps1` 自动维护）。

## 4. 开发与验收（MUST）

- 以 `.claude/harness/features.json` 中的 `acceptance_criteria` 和 `test_command` 为准。
- 至少执行以下验证：

```powershell
cmake --build build --config Debug
ctest --test-dir build -C Debug -R <test_pattern>
```

- 没有构建/测试证据时，不得宣称任务完成。

## 5. Git 提交与推送（MUST）

- 每个任务完成并通过验收后，必须按 `.claude/rules/git-workflow.md` 执行提交与推送。
- 提交信息格式：`<type>: <description>`，例如 `fix: 完成 T014 线程阻塞修复`。
- 推荐命令：

```powershell
git add .
git commit -m "<type>: <description>"
git push
```

- 如果当前目录不是 Git 仓库（例如 `git rev-parse --is-inside-work-tree` 失败），可跳过提交与推送，但必须在 `.claude/harness/claude-progress.txt` 记录“因无 Git 管理而跳过”。

## 6. 需要自动识别的信息

- 主 `CMakeLists.txt` 入口
- 主应用目标名
- 当前 Qt 版本与模块
- 推荐的构建命令与测试命令

## 7. 不可跳过的工作流

- 先依据 PRD 执行 `plan`
- 每次只推进一个 harness 任务
- 每轮任务结束后都要构建和测试
- 及时更新 `.claude/harness/features.json` 与 `.claude/harness/claude-progress.txt`
- 每次状态流转后自动更新 `docs/reports/<任务编号>-任务描述.md`

## 8. 受保护区域

除非当前任务明确要求，否则不要重构现有源码树和目录布局。
