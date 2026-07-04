---
type: reference
audience: new-user
---

# Animus 文档

> 状态机驱动的 AI 编码工作流引擎文档。

---

## 快速入口

| 你的角色 | 你想做什么 | 去哪看 |
|---------|-----------|--------|
| 🆕 **新用户** | 第一次使用，快速上手 | [`tutorials/getting-started.md`](tutorials/getting-started.md) |
| 🔧 **日常用户** | 查某个命令的用法 | [`reference/commands.md`](reference/commands.md) |
| ⚙️ **项目 Lead** | 调整审查规则或配置 | [`how-to/configure-review.md`](how-to/configure-review.md) |
| 🏗️ **插件开发者** | 新增 Agent 或语言支持 | [`how-to/add-new-agent.md`](how-to/add-new-agent.md) |
| 🧠 **好奇者** | 理解状态机或 memlog 设计原理 | [`explanation/state-machine.md`](explanation/state-machine.md) |
| 📋 **维护者** | 查看路线图和规划 | [`bmad-optimization-roadmap.md`](bmad-optimization-roadmap.md) |
| 🔍 **审查者** | 查看配置项清单 | [`reference/config-options.md`](reference/config-options.md) |

---

## 文档分类

| 象限 | 色标 | 适合谁 | 内容特征 |
|------|------|--------|---------|
| **Tutorials** | 🟢 教程 | 新用户 | 完整步骤，零知识假设 |
| **How-To** | 🔵 指南 | 有明确目标的人 | 聚焦单一任务，直接可操作 |
| **Explanation** | 🟡 解释 | 想理解原理的人 | 背景、权衡、设计决策 |
| **Reference** | 🔴 参考 | 所有人都需要 | 精确、完整、可搜索 |

---

## 文档清单

### Tutorials 🟢

- [`getting-started.md`](tutorials/getting-started.md) — 5 分钟上手 Animus

### How-To 🔵

- [`configure-review.md`](how-to/configure-review.md) — 如何调整代码审查严格度
- [`add-new-agent.md`](how-to/add-new-agent.md) — 如何新增一个 Agent
- [`customize-hooks.md`](how-to/customize-hooks.md) — 如何编写自定义 Hook

### Explanation 🟡

- [`architecture.md`](architecture.md) — 架构分层与设计模式
- [`state-machine.md`](explanation/state-machine.md) — 状态机流转规则
- [`memlog-design.md`](explanation/memlog-design.md) — Memlog 事件源设计

### Reference 🔴

- [`commands.md`](reference/commands.md) — 7 个斜杠命令详解
- [`config-options.md`](reference/config-options.md) — 全部配置项说明
- [`agent-index.md`](agent-index.md) — 全部 Agent 索引
- [`hooks-registry.md`](reference/hooks-registry.md) — 钩子注册表
- [`testing.md`](reference/testing.md) — 测试参考
- [`plugin-validator-guide.md`](plugin-validator-guide.md) — 语义验证器审查规则
- [`bmad-optimization-roadmap.md`](bmad-optimization-roadmap.md) — 路线图
- [`dev-verification-plan.md`](dev-verification-plan.md) — 开发与验证计划
