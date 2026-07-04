---
name: party-mode
description: 多 Agent 辩论模式 — 架构评审和代码审查的多方意见碰撞
---

# Party Mode 辩论模式

## 功能

多 agent 并行辩论，从不同角度碰撞观点，暴露设计盲点。

## 预装模板

| 模板 | 角色 | 人数 | 适用场景 |
|------|------|------|---------|
| 架构评审团 | 架构师+审查官+测试官+构建师+规划师 | 5 | `/animus-dev --full` 方案评审 |
| 代码审查团 | 审查官+边界猎手+验收审计官+精简审查官 | 4 | 审查 high 争议 |

## 运行模式

| 模式 | 说明 |
|------|------|
| session | 一个大脑扮演所有角色 |
| subagent | 每个角色独立 spawn 子 agent（推荐） |
| auto | 必要时混入真实 agent |
| agent-team | 持久团队（Claude Code 限定） |

## 辩论流程

1. 方案陈述 — 每个角色发表意见
2. 质疑交锋 — 角色间互相提问
3. 共识/分歧记录
4. 合成输出 — 共识写入 spec，分歧存 report

## 触发方式

- 自动：`/animus-dev --full` 和 `/animus-review`（high 争议时）
- 手动：`/animus-party --template <模板> --mode <模式>`
