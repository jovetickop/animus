---
description: 将 PRD 或方案文档转为 harness 任务列表，并更新 .claude/harness-cc/features.json
---

# /harness-code-plan

## 工作流程

### 阶段一：Grilling 追问

激活本命令后，首先进入 Grilling 追问阶段。使用以下 7 个问题模板逐个向用户提问，每次记录用户回答：

**Q1：核心验收标准是什么？**
> 推荐方向：从用户视角描述，完成后用户能做什么，解决什么具体问题。

**Q2：前置依赖有哪些？**
> 推荐方向：列出已有的模块、接口、表结构、API 或第三方服务。

**Q3：异常流程如何处理？**
> 推荐方向：错误提示、回滚机制、锁定策略、降级方案。

**Q4：性能/安全有什么要求？**
> 推荐方向：加密要求、限流策略、超时设置、并发量级、数据安全。

**Q5：架构约束有哪些？**
> 推荐方向：分层架构、设计模式、目录结构、技术栈选型限制。

**Q6：风险在哪里？**
> 推荐方向：并发竞争、边界条件、第三方依赖、未知领域。

**Q7：测试策略是什么？**
> 推荐方向：单元测试、集成测试、E2E 测试、手动测试、覆盖率目标。

**Grilling 流程：**
1. AI 逐个提问，每次等待用户回答后再问下一题。
2. 用户回答后立即追加写入 `.claude/harness-cc/plan-context.md`（格式参考 `${CLAUDE_PLUGIN_ROOT}/templates/harness/plan-context.md`）。
3. 全部 7 问完成后，AI 读取完整的 `plan-context.md` 作为后续规划输入。

### 阶段二：任务规划

Grilling 完成后，使用 feature-planner agent 将 PRD（及方案文档，如有）拆解为可执行任务列表。

**必须读取：**
- `${CLAUDE_PLUGIN_ROOT}/agents/universal/feature-planner.md` 了解完整规则
- `.claude/harness-cc/plan-context.md`（Grilling 追问结果，作为规划输入）
- `.claude/harness-cc/features.json`（如存在，作为基线参考）

**产出：**
- 更新或创建 `.claude/harness-cc/features.json`
- 完成后可运行 `${CLAUDE_PLUGIN_ROOT}/commands/validate-features.ps1` 验证结构
