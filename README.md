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

## v1.5 亮点

| 功能 | 说明 |
|------|------|
| **Agent 编号菜单** | 12 个核心 Agent 激活后展示数字编号菜单（1 2 3 4），意图明确时自动跳过 |
| **文档四象限重组** | 文档按 Tutorials / How-To / Explanation / Reference 四象限组织，入口导航 `docs/README.md` |
| **双模式插件验证器** | `python scripts/plugin-validator.py` — 8 条确定性规则 + `--json`/`--strict`/`--fix` |
| **语义审查规则** | `docs/plugin-validator-guide.md` — AI 可读的 8 条语义规则，插件重构后自动审查 |
| **纯 Python 运行时钩子** | 移除全部 Shell 脚本和 `jq` 依赖，hooks 纯 Python 实现，兼容 2/3 |
| **配置 JSON 化** | `.claude/animus/config.json` — 零第三方库依赖，纯标准库 `json` |

## 技能

| 技能 | 用途 |
|------|------|
| 辩论模式 (Party Mode) | 架构评审/代码审查（含预装模板） |
| 头脑风暴 | 6 个技法（PRFAQ/第一性原理/SCAMPER/逆向思维/坏人测试/竞品评测） |
| 系统性调试 | Bug 系统化修复流程 |
| TDD 工作流 | 测试驱动开发流程 |

## 文档导航

详见 [docs/README.md](docs/README.md) 四象限入口。
