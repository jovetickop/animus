# 优化任务 ③：`/animus-help` 命令

> 对应路线图：Phase 1 — 快速见效 / P0（③ 命令别名与 Help）
> 解决：新用户不知道有哪些命令、不知道当前该做什么

---

## 一、更改原因

### 1.1 当前问题

- 8 个 `animus-` 前缀命令，新用户翻文档才知道用哪个
- 想做短别名（如 `/plan`）但容易跟官方或其他插件冲突
- 执行完一个命令后，用户不知道"下一步做什么"
- 没有入口能展示"当前项目进度 + 可选操作"

### 1.2 解决后的效果

- 一个入口解决所有"接下来干嘛"的疑问
- 根据 `.claude/animus/` 当前状态动态推荐下一步
- 不再需要记 8 个命令名，从 `/animus-help` 的推荐列表点就行

---

## 二、更改方案

### 2.1 命令别名

在 `plugin.json` 中为高频命令加简短别名：

| 当前命令 | 别名 | 触发场景 |
|---------|------|---------|
| `/animus-dev` | `/dev` | "我要改点东西"、"开始干活" |
| `/animus-status` | `/status`、`/progress` | "现在到哪了"、"任务进度" |
| `/animus-debug` | `/debug` | "有个 bug"、"不 work" |
| `/animus-review` | `/review` | "帮我检查"、"验收" |
| `/animus-handoff` | `/save`、`/checkpoint` | "先到这"、"保存状态" |
| `/animus-continue` | `/load`、`/resume` | "继续上次"、"恢复" |

### 2.2 帮助命令设计

```
/animus-help

输出：
  ┌─────────────────────────────────┐
  │  animus 帮助                      │
  │                                   │
  │  📋 当前进度：3/8 任务完成 (37%)    │
  │                                   │
  │  💡 推荐下一步：                    │
  │     /animus-dev 开始实施 T004-T006 │
  │     或用 --full 做完整需求分析      │
  │                                   │
  │  📖 全部命令：                      │
  │     /animus-dev   — 开发入口       │
  │     /animus-review — 代码审查       │
  │     /animus-debug  — 系统化调试     │
  │     /animus-status — 状态看板       │
  │     /animus-handoff — 保存状态      │
  │     /animus-continue — 恢复状态     │
  │     /animus-archive — 迭代归档      │
  │     /animus-init  — 项目初始化     │
  └─────────────────────────────────┘
```

### 2.2 推荐逻辑

读取 `.claude/animus/` 目录状态，按优先级规则推荐：

| 当前状态 | 推荐命令 | 理由 |
|---------|---------|------|
| 无 features.json | `/animus-init` | 项目还没初始化 |
| features.json 无任务 | `/animus-dev` | 还没拆需求，建议规划 |
| 有待办任务 (pending) | `/animus-dev` | 有任务等实施 |
| 有进行中任务 (in_progress) | `/animus-dev` | 继续当前任务 |
| 有已完成任务未审查 | `/animus-review` | 代码需要审查 |
| 审查不通过 | `/animus-dev` | 有任务需要修复 |
| 全部通过 / 迭代结束 | `/animus-archive` 或 `/animus-handoff` | 归档或保存 |

### 2.3 改动文件

| 文件 | 改动 |
|------|------|
| 新建 `commands/animus-help.md` | 命令本体 |
| `.claude-plugin/plugin.json` `commands` 数组 | 注册新命令 |

### 2.4 命令文件结构

```markdown
---
name: animus-help
description: 显示 animus 帮助和推荐下一步操作
---
# /animus-help

## 功能
列出所有 animus 命令及用途，根据当前项目状态推荐下一步。

## 流程

1. 读取 `.claude/animus/features.json`（如果存在）
2. 读取 `.claude/animus/project-config.json`
3. 根据状态决定推荐（见上方推荐逻辑表）
4. 输出格式化的帮助信息
```

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 无影响——只读 features.json，不做任何写入 |
| 兼容性 | 完全向后兼容——新旧 features.json 格式均可读取 |
| 降级 | features.json 损坏或不存在时正常输出"未初始化"提示，不 crash |

## 四、验证方法

1. 在未初始化的项目执行 `/animus-help` → 推荐 `/animus-init`
2. 在有 features.json 但无任务的项目执行 → 推荐 `/animus-dev`
3. 在有 in_progress 任务的项目执行 → 推荐 `/animus-dev` 继续
4. 确认全部命令别名在 plugin.json 中注册正确
