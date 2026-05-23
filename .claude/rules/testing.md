# 测试规范

## 基线要求

- 只要变更不是纯文档，就必须至少完成构建和相关测试。
- 新行为应补充测试；如果不能补测试，必须说明原因。
- 验证命令要写入 `.claude/harness/features.json`。

## 覆盖建议

每个功能级任务至少考虑：

- 正常输入
- 空输入
- 无效输入
- 边界值
- 邻近逻辑的回归风险

## Qt/CMake 验证

按项目实际情况执行，例如：

```bash
cmake -B build -DBUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

## 任务通过规则

只有满足以下条件，任务才能标记为 `passed`：

- 构建成功
- 相关测试通过
- 结果已经写入 `.claude/harness/claude-progress.txt`

如果构建或测试失败，先把失败摘要写入进度日志，再把任务回退到 `pending`。
