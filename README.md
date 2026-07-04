# animus

Claude Code 编码工作流引擎。任务拆解编排、进度持久化、跨会话恢复、自动审查门控。

## 安装

```
/plugin marketplace add jovetickop/animus
/plugin install animus@animus
```

## 命令

| 命令 | 用途 |
|------|------|
| `/animus-init` | 项目初始化 |
| `/animus-dev` | 统一开发入口（debug/fast/light/full 四路路由） |
| `/animus-review` | 代码审查（4 agent 并行） |
| `/animus-party` | 辩论模式（架构评审/代码审查） |
| `/animus-status` | 状态看板 + 推荐下一步 |
| `/animus-help` | 帮助与导航 |
| `/animus-archive` | 迭代归档 |

## 日常流程

```
/animus-dev <需求描述>  → 实现 → /animus-review → /animus-archive
```

## 技能

| 技能 | 用途 |
|------|------|
| 辩论模式 (Party Mode) | 架构评审/代码审查（含预装模板） |
| 头脑风暴 | 6 个技法（PRFAQ/第一性原理/SCAMPER/逆向思维/坏人测试/竞品评测） |
| 系统性调试 | Bug 系统化修复流程 |
| TDD 工作流 | 测试驱动开发流程 |

## 详细指南

详见 [docs/guide.md](docs/guide.md)
