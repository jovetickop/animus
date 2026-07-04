---
name: animus-help
search_phrases: ["/help", "帮助", "guide", "command", "命令"]
description: 列出所有 animus 命令及推荐下一步
---

# /animus-help — 帮助与导航

## 功能

列出所有可用命令，根据当前项目状态推荐下一步。

## 当前命令

| 命令 | 用途 |
|------|------|
| `/animus-init` | 项目初始化 |
| `/animus-dev` | 统一开发入口（四路路由） |
| `/animus-review` | 代码审查 |
| `/animus-party` | 辩论模式 |
| `/animus-status` | 状态看板 |
| `/animus-help` | 帮助与导航 |
| `/animus-archive` | 迭代归档 |

## 推荐逻辑

读取 features.json，按状态推荐：
- 无 features.json → `/animus-init`
- 有 pending 任务 → `/animus-dev`
- 有 passed 任务未审查 → `/animus-review`
- 全部 passed → `/animus-archive`
