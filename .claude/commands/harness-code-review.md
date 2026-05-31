---
description: 执行通用检查 + 按项目类型的专项验收检查
---

# /harness-code-review

请使用 code-reviewer agent 对当前变更进行全面审查。

- 读取 `.claude/agents/universal/code-reviewer.md` 了解审查细则
- 按 project-type 执行对应的语言专项检查
- 输出严重级别和修复建议
- 给出明确结论：通过 / 有条件通过 / 不通过

辅助验证脚本：
- `.claude\commands\validate-features.ps1` — 验证 features.json 结构
- `.claude\commands\check-consistency.ps1` — 检查状态一致性
