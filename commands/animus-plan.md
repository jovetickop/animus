---
description: 将 PRD 或方案文档转为 harness 任务列表，并更新 .claude/animus/features.json
---

# /animus-plan

## 智能分派

用户可以在启动命令时提供文档路径（在对话中说"我要实现登录功能，方案在 ./docs/login-plan.md"），
或者直接在对话中粘贴文档内容。
AI 检测到有文档时自动读取并生成针对性追问。
没有文档时使用固定 7 问模板兜底。

---

## 工作流程

### 阶段一：Grilling 追问

激活本命令后，根据上方"智能分派"判断进入对应分支：

- **有文档分支**：读取文档 → 自动理解 → 针对性追问（只问文档未覆盖部分）→ 术语提取
- **无文档分支**：使用以下 7 个问题逐个进行互动式提问

**Grilling 规范：**

每个问题必须使用 `AskUserQuestion` 工具进行互动式提问，提供结构化选项供用户选择，同时支持自定义输入。

**标准结构：**
- `question` — 问题正文（与模板一致）
- `header` — 简短标签（如 Q1、Q2）
- `options` — 2-4 个推荐方向作为选项（从"推荐方向"中提取），每次均需包含一个"其他（自定义）"选项
- `multiSelect: true` — 允许用户选择多个选项

**无文档分支 — Q1~Q7 模板如下：**

| # | 问题 | 推荐方向（选项） |
|---|------|----------------|
| **Q1** | 核心验收标准是什么？ | 从用户视角描述 / 完成后能解决什么问题 / 开发完成后如何验证 |
| **Q2** | 前置依赖有哪些？ | 已有模块/接口 / 数据表结构 / 第三方服务 / API |
| **Q3** | 异常流程如何处理？ | 错误提示策略 / 回滚机制 / 锁定策略 / 降级方案 |
| **Q4** | 性能/安全有什么要求？ | 加密要求 / 限流策略 / 超时设置 / 并发量级 / 数据安全 |
| **Q5** | 架构约束有哪些？ | 分层架构 / 设计模式 / 目录结构 / 技术栈选型限制 |
| **Q6** | 风险在哪里？ | 并发竞争 / 边界条件 / 第三方依赖 / 未知领域 |
| **Q7** | 测试策略是什么？ | 单元测试 / 集成测试 / E2E / 手动测试 / 覆盖率目标 |

**Grilling 流程：**
1. AI 逐个使用 `AskUserQuestion` 提问，提供上述推荐方向作为选项
2. 用户选择后立即追加写入 `.claude/animus/plan-context.md`（格式参考 `${CLAUDE_PLUGIN_ROOT}/templates/animus/plan-context.md`）
3. 用户选择"其他（自定义）"时等待用户输入文本
4. 全部 7 问完成后，AI 读取完整的 `plan-context.md` 作为后续规划输入

> **术语提取**：Grilling 全部完成后，从用户回答中提取领域术语，写入 `.claude/animus/domain-lexicon.md`。特别关注 Q1（验收标准）中的业务概念和 Q5（架构约束）中的技术术语。

### 阶段二：任务规划

Grilling 完成后，使用 feature-planner agent 将 PRD（及方案文档，如有）拆解为可执行任务列表。

**必须读取：**
- `${CLAUDE_PLUGIN_ROOT}/agents/universal/feature-planner.md` 了解完整规则
- `.claude/animus/plan-context.md`（Grilling 追问结果，作为规划输入）
- `.claude/animus/features.json`（如存在，作为基线参考）

**产出：**
- 更新或创建 `.claude/animus/features.json`
- 完成后可运行 `${CLAUDE_PLUGIN_ROOT}/commands/validate-features.ps1` 验证结构
