---
name: animus-party
search_phrases: ["/party", "debate", "辩论", "评审", "review"]
description: 多 Agent 辩论模式 — 架构评审和代码审查的多方意见碰撞
---

# /animus-party — 辩论模式

## 功能

多 agent 并行辩论，从不同角度碰撞观点，暴露设计盲点。

## 模板

| 模板 | 角色 | 人数 | 适用场景 |
|------|------|------|---------|
| `arch-review` | 架构师+审查官+测试官+构建师+规划师 | 5 | 架构方案评审 |
| `code-review` | 审查官+边界猎手+验收审计官+精简审查官 | 4 | 审查有争议时 |

## 运行模式

| 模式 | 说明 |
|------|------|
| `session` | 一个大脑扮演所有角色轮流发言，快速辩论 |
| `subagent` | 每个角色独立 spawn 子 agent，深度辩论（推荐） |
| `auto` | 根据复杂度自动选择 session 或 subagent |
| `agent-team` | 持久团队（Claude Code 限定） |

## 辩论流程

1. 方案陈述 — 每个角色发表意见
2. 观点碰撞 — 跨角色提问和反驳
3. 收敛 — 识别共识点，标注分歧点
4. 结论 — 输出裁决报告

## 触发方式

**自动触发：** 在 `config.toml` 中配置 `[party_mode].auto_trigger`：
- `["dev-full"]` — 执行 full-path 开发时自动触发
- `["review-controversial"]` — 审查中发现争议时自动触发

**手动触发：** `/animus-party [--template arch-review] [--mode subagent]`

## 配置

```toml
[party_mode]
default_mode = "subagent"
default_party = "arch-review"
auto_trigger = ["dev-full", "review-controversial"]
ask_before_start = true
max_rounds = 3
```

## 参考

详见 `skills/party-mode/SKILL.md`。
