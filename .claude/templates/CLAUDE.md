# 项目级工作约定

## 1. 自动识别命令（setup MUST 填写）

- 配置命令：`<AUTO_DETECTED_CONFIGURE_COMMAND>`
- 构建命令：`<AUTO_DETECTED_BUILD_COMMAND>`
- 测试命令：`<AUTO_DETECTED_TEST_COMMAND>`
- 运行命令：`<AUTO_DETECTED_RUN_COMMAND>`

- `setup` 必须在接入阶段自动探测并回填以上命令。
- 不允许保留 `<AUTO_DETECTED_...>` 占位符。
- 如果测试不可用，必须写明原因和推荐补齐方案。

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
- 提交信息格式：`<type>: <description>`，例如 `feat: 完成 T003 主窗口菜单行为`。
- 推荐命令：

```powershell
git add .
git commit -m "<type>: <description>"
git push
```

- 如果当前目录不是 Git 仓库（例如 `git rev-parse --is-inside-work-tree` 失败），可跳过提交与推送，但必须在 `.claude/harness/claude-progress.txt` 记录“因无 Git 管理而跳过”。

## 6. 核心节奏

- 先读 PRD，再执行 `plan`
- 每轮只推进一个任务
- 每个任务结束都要构建和测试
- 每次结果都写入 `.claude/harness/claude-progress.txt`
- 每次状态流转后自动更新 `docs/reports/<任务编号>-任务描述.md`

## 7. 必须长期维护的文件

- `.claude/harness/features.json`
- `.claude/harness/claude-progress.txt`
- `docs/reports/`
- `.claude/rules/`

## 8. 需要人工补充的项目特有信息

- 禁止修改的目录
- 项目架构约束
