# Animus 详细指南

> 本指南包含架构说明、命令详解、配置项、扩展开发等内容。

---

## 目录

1. [架构总览](#架构总览)
2. [命令详解](#命令详解)
3. [五路开发路由](#五路开发路由)
4. [配置系统](#配置系统)
5. [状态机](#状态机)
6. [Memlog 事件源](#memlog-事件源)
7. [引擎 CLI](#引擎-cli)
8. [审查门控](#审查门控)
9. [Agent 体系](#agent-体系)
10. [钩子系统](#钩子系统)

---

## 架构总览

```
插件入口 (.claude-plugin/plugin.json)
  → 编排层 (commands/*.md)
    → 引擎层 (scripts/animus-engine.py)
      → 子命令模块 (scripts/engine/*.py)
        → 持久化层 (features.json + memlog/)
        → 配置层 (config.toml 两层覆盖)
```

### 核心设计

- **状态机驱动**：任务状态流转严格校验，非法流转 exit 1
- **单一事件源**：memlog 记录所有事件，features.json 由 memlog 派生重建
- **两层配置**：defaults → config.toml
- **分层 Agent**：base/ → universal/ → {lang}/ 继承机制

---

## 命令详解

### `/animus-dev` — 统一开发入口

处理所有开发场景。五路路由自动分流：

| 路径 | 触发条件 | 流程 |
|------|---------|------|
| debug | bug 报告/异常/回归 | 3 问调试 → features.json → implement → review |
| oneshot | 零爆炸半径（改颜色值） | 1 句确认 → implement → review |
| fast | 1-2 文件/小改动 | 1 句确认 → implement → review |
| light | 3-10 文件/新增功能 | 3 问 → features.json → implement → review |
| full | 跨模块/架构改动 | 7 问 + 可选脑暴 → 拆任务 → implement → review |

AI 自动选路后输出「将使用 XX 路径」让用户确认。`config.toml` 中 `autonomous = true` 时跳过确认。

启动时自动检测 memlog→若有历史事件则自动恢复 features.json。

### `/animus-review` — 代码审查

4 agent 并行审查：

| Agent | 重点 |
|-------|------|
| 审查官 (Review) | 正确性、安全、竞态 |
| 边界猎手 | 空值、溢出、并发、资源泄露 |
| 验收审计官 | 逐条核对 features.json spec.success |
| 精简审查官 | 过度工程、可删减代码 |

审查分级：HIGH 阻塞 / MEDIUM 人工确认 / LOW 自动通过。不合格可退回 implementer 修复后重审（最多 3 轮）。

### `/animus-status` — 状态看板

显示任务统计 + 每个任务明细 + 推荐下一步。

### `/animus-help` — 帮助与导航

根据当前项目状态动态推荐命令。

### `/animus-setup` — 项目初始化

检测项目类型（cpp-qt/cpp-cmake/rust/go/node/python），创建运行时目录。

### `/animus-archive` — 迭代归档

归档当前 features.json → archive/iter-xxx/ 目录 + 清空 + 生成迭代总结。

### `/animus-config` — 配置管理

查看当前生效的配置、校验合法性。

---

## 五路开发路由

```
用户输入 → AI 检测意图类型
  ├── bug 报告/异常 → debug-path（3 问调试专用）
  ├── 零爆炸半径 → oneshot（1 句确认）
  ├── 1-2 文件/小改动 → fast-path（1 句确认）
  ├── 3-10 文件/新增 → light-path（3 问）
  └── 跨模块/架构改动 → full-path（7 问 + 可选脑暴）
```

### Debug 路径 3 问

1. 复现步骤与影响范围
2. 根因初步推断
3. 修复策略与副作用评估

### Full 路径 7 问

1. 验收标准
2. 前置依赖
3. 异常流程
4. 性能/安全
5. 架构约束
6. 风险
7. 测试策略

---

## 配置系统

两层覆盖：`defaults（硬编码） ← config.toml`

文件位置：`.claude/animus/`

| 段 | 字段 | 说明 |
|----|------|------|
| `[dev]` | `default_path` | 默认路径（auto/fast/light/full/oneshot） |
| | `autonomous` | 自主模式（true 时 AI 全权决策） |
| `[review]` | `strictness` | 严格度（low/normal/high） |
| | `max_findings` | 最多输出问题数 |
| `[gates]` | `require_task_before_write` | 写代码门控 |
| `[ponytail]` | `enabled` / `max_lines_per_file` | 精简审查 |
| `[party_mode]` | `default_mode` / `default_party` / `auto_trigger` / `ask_before_start` / `max_rounds` | 辩论配置 |

文件不存在时回退硬编码默认值。配置读取路径：
```python
python animus-engine.py validate  # 也可以验证配置
```

---

## 状态机

### 状态流转

```
pending → in_progress → passed → completed
                    ↘ failed → in_progress/pending
```

- `pending → in_progress`：前置依赖全部 passed（如果有）
- `in_progress → passed`：通过 Oracle 验证门控（verify_command）
- `in_progress → failed`：必须提供原因
- `failed → in_progress`：重试
- `completed`：终态（可重入 in_progress）

### 限制

- 同时只能有一个 `in_progress` 任务
- `depends_on` 构建 DAG，只能依赖直接前置任务
- 非法流转 `exit 1`

### CLI 使用

```bash
python animus-engine.py transition T001 in_progress
python animus-engine.py transition T001 passed --evidence "test all pass"
```

---

## Memlog 事件源

### 目录结构

```
.claude/animus/memlog/
├── 2026-07-04-1001-创建任务-T003-添加PDF导出功能.md
├── 2026-07-04-1030-状态变更-T003-进行中.md
├── 2026-07-04-1100-决策-选择QProcess作为后端.md
├── 2026-07-04-1130-归档-迭代003.md
├── 2026-07-04-1400-辩论-架构评审-T003.md
└── ...
```

### 事件类型

| 类型 | 说明 |
|------|------|
| 创建任务 | 任务创建时写入 |
| 状态变更 | 状态流转时写入 |
| 决策 | 技术/架构决策时写入 |
| 交接 | 记录交接时刻（traceability） |
| 归档 | 归档迭代时写入 |
| 辩论 | Party Mode 辩论全量日志 |

### 核心原则

- **append-only**：memlog 永不删除、永不归档
- **单一事件源**：features.json 由 memlog 派生，可删除重建
- **重建命令**：`python animus-engine.py rebuild`

---

## 引擎 CLI

统一入口 `scripts/animus-engine.py`，子命令：

| 命令 | 功能 |
|------|------|
| `status` | 显示任务状态 |
| `transition <id> <to>` | 状态流转 |
| `validate` | 校验 features.json |
| `archive` | 归档迭代 |
| `rebuild` | 从 memlog 重建 |

```bash
python animus-engine.py status
python animus-engine.py transition T001 in_progress
python animus-engine.py validate
python animus-engine.py archive --name "迭代名称"
python animus-engine.py rebuild
```

---

## 审查门控

| 门控 | 级别 | 说明 |
|------|------|------|
| Write 前门控 | HARD | 无 in_progress 任务时拒绝 Write/Edit |
| Oracle 验证 | HARD | to=passed 时执行 verify_command |
| 并行审查 | HARD | 4 agent 审查，high 阻塞 |
| 循环回退 | HARD | 最多 3 轮，超限终止 |
| 超时降级 | HARD | 单 agent 重试 3 次，失败终止 |
| SPEC 法则 | SOFT | 4 条法则校验，违规警告 |

---

## Agent 体系

### 分组

| 组 | 数量 | Agent |
|----|------|-------|
| universal | 8 | 规划师/实现者/测试官/构建师/审查官/边界猎手/验收审计官/精简审查官 |
| qt | 4 | 架构师/实现者/测试官/UI 审查官 |
| cpp-cmake | 1 | 架构师 |
| python | 2 | 架构师/测试官 |
| node | 3 | 架构师/测试官/UI 审查官 |
| rust | 2 | 架构师/测试官 |
| go | 2 | 架构师/测试官 |
| frontend | 1 | 规划师 |
| base | 2 | 核心模板（实现者/测试官）|

### 命名规则

每个 agent frontmatter 包含：
```yaml
---
name: 审查官 (Review)
title: 代码质量门控审查
team: universal
persona: 你叫审查官 (Review)。一行不放过...
---
```

---

## 钩子系统

| 钩子 | 触发时机 | 作用 | 超时 |
|------|---------|------|------|
| PreToolUse | Write/Edit 前 | write-gate 门控 + 备份 features.json + GBK→UTF-8 | 5s + 10s |
| PostToolUse | Write/Edit 后 | clang-format + format-all 多语言格式化 + UTF-8→GBK | 10s + 15s |
| PreCompact | 上下文压缩前 | JSONL compact 事件 + 状态看板同步 | 10s |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 | 10s |

所有钩子双平台（bash + PowerShell），失败 `exit 0` 不阻塞。

---

## 安装目录结构

```
项目根目录/
├── .claude/
│   └── animus/
│       ├── config.toml           # 配置（git 跟踪）
│       ├── features.json         # 任务状态（由 memlog 派生）
│       ├── memlog/               # 事件源目录
│       ├── project-config.json   # 项目类型配置
│       └── archive/              # 归档目录
├── .claude-plugin/
│   └── plugin.json               # 插件清单
├── commands/                     # 斜杠命令
├── agents/                       # Agent 定义
├── hooks/                        # 运行时钩子
├── scripts/                      # Python 脚本
│   ├── animus-engine.py          # 统一 CLI 入口
│   ├── engine/                   # 子命令模块
│   └── config_loader.py          # 配置加载器
└── skills/                       # 技能定义
    ├── party-mode/               # 辩论模式
    └── brainstorming/            # 头脑风暴
```
