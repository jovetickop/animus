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
| `/dev` | 统一开发入口（debug/oneshot/fast/light/full 五路路由） |
| `/review` | 代码审查（4 agent 并行） |
| `/status` | 状态看板 + 推荐下一步 |
| `/help` | 帮助与导航 |
| `/animus-setup` | 项目初始化 |
| `/animus-archive` | 迭代归档 |
| `/animus-config` | 配置管理（三层覆盖） |

## 日常流程

```
/dev <需求描述>  → 实现 → /review → /archive
```

## 详细指南

详见 [docs/guide.md](docs/guide.md)
