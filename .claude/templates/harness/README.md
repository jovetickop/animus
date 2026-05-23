# Harness 执行指令

只按下面流程执行。

1. 读取 `.claude/harness/features.json`，优先选择 `in_progress` 任务；若不存在，从 `pending` 中选择“依赖已满足且 `priority` 最大”的任务。
2. 若任务是 `pending`，将其标记为 `in_progress`；若已是 `in_progress`，直接续做并写入进度日志。
3. 只实现当前任务，不跨任务修改
4. 如果当前任务支持多智能体/Teams执行，请自动进行
5. 执行 `CLAUDE.md` 里的构建命令和当前任务的 `test_command`。
6. 构建或测试失败时，记录失败原因并将任务标记为 `failed`。
7. 构建和测试都通过时，将任务标记为 `passed`，并写入验证结果。
8. 按 `.claude/rules/git-workflow.md` 执行 `git add`、`git commit`、`git push`；若无 Git 管理则跳过并记录原因。
9. 如需重试失败任务，先将其从 `failed` 改为 `in_progress`，再继续执行。
10. 重复步骤 1，直到没有 `in_progress` 且没有 `pending` 任务。

硬规则：

- 没有构建和测试结果，禁止标记 `passed`。
- `moc`/`uic`/`rcc` 失败等价于任务失败。
- 每轮都必须更新 `.claude/harness/claude-progress.txt`。
- 每次任务状态流转后，必须自动更新 `docs/reports/<任务编号>-任务描述.md`，沉淀“功能描述 + 最新验证结果”。
- 失败任务默认保持 `failed`，不要自动回退到 `pending`。
- `depends_on` 只写直接依赖；依赖任务必须先 `passed`，当前任务才能进入 `in_progress`。
- `updated_at` 与 `last_error` 由 `update-progress.ps1` 自动维护，不要手工批量改写。
