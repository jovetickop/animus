# Hook 调试指南

已整合至 [docs/guide.md](guide.md#钩子系统)。4 种钩子 + 调试模式。

- PreToolUse：Write/Edit 前（write-gate 门控 + 备份）
- PostToolUse：Write/Edit 后（格式化）
- PreCompact：上下文压缩前
- Stop：会话结束时

调试：`ANIMUS_DEBUG=true` 环境变量
