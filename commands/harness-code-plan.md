---
description: 将 PRD 或方案文档转为 harness 任务列表，并更新 .claude/harness/features.json
---

# /harness-code-plan

请使用 feature-planner agent 将 PRD（及方案文档，如有）拆解为可执行任务列表。

- 读取 `.claude/agents/universal/feature-planner.md` 了解完整规则
- 更新或创建 `.claude/harness/features.json`
- 完成后可运行 `.claude\commands\validate-features.ps1` 验证结构
