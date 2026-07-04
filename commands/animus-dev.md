---
name: animus-dev
search_phrases: ["/dev", "develop", "implement", "代码", "开发", "bug", "debug", "修复", "feature"]
description: 统一开发入口（五路路由：debug/oneshot/fast/light/full）
---

# /animus-dev — 统一开发入口

## 功能

一个入口处理所有开发场景：从改个颜色到架构设计，从修 bug 到加新功能。

## 五路路由

| 路径 | 触发条件 | 说明 |
|------|---------|------|
| **debug** | bug 报告/异常/回归 | 3 问调试专用 Grilling（复现→根因→修复策略） |
| **oneshot** | 零爆炸半径（改个颜色值） | 0 问，直接实施 |
| **fast** | 1-2 文件 / 小改动 | 1 句确认 |
| **light** | 3-10 文件 / 新增功能 | 3 问 |
| **full** | 跨模块 / 架构改动 | 7 问 + 可选脑暴 |

## 路径确认

AI 自动检测意图类型后输出「将使用 XX 路径」让用户确认。
配置文件 config.toml 中 `dev.autonomous = true` 时跳过确认。

## 任务门控

所有路径都写 features.json，agent 没有任务不能写代码。
配合 PreToolUse hook（write-gate）做硬拦截。

## 自动恢复

启动时检测 memlog 是否有事件。有 → 自动重建 features.json。

## 参考

详见 `task-05-QuickDev.md` 和 `task-debug-merge-dev.md`。
