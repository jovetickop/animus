---
name: brainstorming
description: 6 种头脑风暴技法 — 集成到 /animus-dev --full 的 7 问之前
---

# 头脑风暴 / 产品发现

## 功能

集成到 `/animus-dev --full` 的 7 问之前，帮助用户理清需求。

## 6 个技法

| # | 技法 | 文件 | 适用场景 | 核心问题 |
|---|------|------|---------|---------|
| 1 | PRFAQ | `PRFAQ.md` | 不知道做什么 | 写一篇功能发布公告 |
| 2 | 第一性原理 | `first-principles.md` | 方案太复杂 | 拆到基本元素再重建 |
| 3 | SCAMPER | `SCAMPER.md` | 优化已有功能 | 替代/结合/改造/换用/消除 |
| 4 | 逆向思维 | `reverse-thinking.md` | 卡住了 | 换一个目标 |
| 5 | 坏人测试 | `bad-guy-test.md` | 不确定什么是好 | 怎么搞坏它 |
| 6 | 竞品评测 | `competitor-evaluation.md` | 同质化竞争 | 假装评别人 |

## 触发

- `/animus-dev --full` 的 7 问之前
- 用户说“不确定”“不知道”时自动检测并询问是否启动脑暴

## 输出

分析结果自动写入 features.json 的 spec 字段。
