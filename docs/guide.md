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

**原理：** 根据用户输入的意图描述，AI 自动判断改动范围和类型，选择最合适的开发路径。所有路径都会写入 memlog 和 features.json，确保任务全程可追溯。

**四路自动分流：**

| 路径 | 触发条件 | 流程 | 用途示例 |
|------|---------|------|---------|
| debug | bug 报告/异常/回归 | 3 问（复现→根因→修复策略）→ features.json → implement → review | "PDF 导出崩溃" |
| fast | 1-2 文件/小改动 | 1 句确认 → 创建 task → features.json → implement → review | "改按钮颜色" |
| light | 3-10 文件/新增功能 | 3 问 → features.json → 拆任务 → implement → review | "加导出功能" |
| full | 跨模块/架构改动 | 7 问 + 可选脑暴 → 拆任务队列 → implement → review | "重构数据层" |

**路径确认：** AI 选路后输出「检测到 XX，将使用 XX 路径」，用户确认后执行。`config.toml` 中 `dev.autonomous = true` 时跳过确认，AI 全权决策。

**自动恢复：** 启动时检测 `.claude/animus/memlog/` 是否有事件。有 → 自动执行 `python animus-engine.py rebuild` 恢复 features.json，输出「检测到上次进度，已恢复」。

**debug 路径诊断流程：**

**第 1 步 — 3 问定位：**
1. 复现步骤与影响范围 — 什么操作触发的？预期 vs 实际？影响哪些用户？
2. 根因初步推断 — 根据症状怀疑哪层的问题？有日志或堆栈吗？
3. 修复策略与副作用评估 — 修复会影响哪些已有功能？需要加什么测试？

**第 2 步 — 无法复现？走穷举分析：**
```
无法稳定复现
  ├── 日志狩猎 — 检查应用/系统日志，找异常堆栈、panic、超时记录
  ├── 路径穷举 — Edge Case Hunter 模式，遍历所有分支路径
  │    标出竞态条件、超时窗口、未处理的边界、隐式分支（枚举缺 case）
  ├── 埋点策略 — 在可疑路径加日志/计数器，输出到独立文件
  └── 环境差异 — 对比用户环境 vs 开发环境的版本、配置、资源限制
```

**第 3 步 — 分层诊断（判断 bug 来源层级）：**
- **意图层** — 需求理解本身不对 → 回到需求澄清，不在此层修代码
- **规范层** — spec 边界不够强，导致实现走偏 → 回退修改 spec 再重做
- **实现层** — 本地代码写错了 → 直接补代码 patch
- 原则：**实现错了是因为意图错了，补代码是错误修复。诊断出在哪一层就在哪一层修。**

**第 4 步 — 审查分诊（5 类）：**

| 标签 | 含义 | 处理 |
|------|------|------|
| `intent_gap` | 意图捕获不完整导致的 bug | 回滚 → 找用户确认意图 |
| `bad_spec` | spec 边界不够强，实现走偏 | 回滚 → 修 spec → 重新实现 |
| `patch` | 局部代码缺陷 | 直接自动修复 |
| `defer` | 存量问题，不是本次引入的 | 记入 `deferred-work.md`，不打断主线 |
| `reject` | 误报 | 静默丢弃 |

**处理顺序：** 先处理 intent_gap 和 bad_spec（代码会被重推），再处理 patch。最多 3 轮修复循环，超限挂起人工介入。

**full 路径 7 问：**
1. 验收标准 — 从用户视角描述，完成后怎么验证
2. 前置依赖 — 已有模块、数据表、第三方服务
3. 异常流程 — 错误提示策略、回滚、降级
4. 性能/安全 — 加密、限流、超时、并发量级
5. 架构约束 — 分层、设计模式、技术栈限制
6. 风险 — 并发竞争、边界条件、第三方依赖
7. 测试策略 — 单元测试、集成测试、E2E

**配置：**
```toml
[dev]
default_path = "auto"    # 默认路径倾向
autonomous = false       # true=AI全权决策，不询问
```

---

### `/animus-review` — 代码审查

**原理：** 并行启动 4 个审查 agent，分别从正确性、边界条件、验收标准、精简度四个维度审查代码。审查结果汇总后按严重度分级裁决。

**4 agent 并行审查：**

| Agent | 重点检查项 | 输出示例 |
|-------|-----------|---------|
| 审查官 (Review) | 正确性 bug、安全漏洞、竞态条件、空指针 | `src/main.cpp:42: HIGH 空指针解引用` |
| 边界猎手 | 空值、溢出、并发、资源泄露、超时、零值 | `src/calc.cpp:15: MEDIUM 整数溢出风险` |
| 验收审计官 | 逐条核对 features.json spec.success | `T005: PASS 导出路径可选` |
| 精简审查官 | 过度工程、可删减抽象、重复代码 | `src/parser.cpp:88: LOW 接口多一层包装` |

**门控规则：**

| 审查结果 | 处理 |
|---------|------|
| 全部 agent 无 high 级问题 | ✅ 允许 passed |
| 有 high 级问题 | ❌ 阻塞，退回 implementer 修复 |
| 有 medium 问题 | ⚠️ 标记待人工确认，不阻塞 |
| 有 low 问题 | ✅ 自动通过，计入报告 |

**5 类分诊：** 每条审查发现按来源分级处理：

| 标签 | 含义 | 处理 |
|------|------|------|
| `intent_gap` | 意图捕获不完整 | 回滚 → 找用户确认意图 |
| `bad_spec` | spec 边界不够强 | 回滚 → 修 spec → 重做 |
| `patch` | 局部代码缺陷 | 自动修复 |
| `defer` | 存量问题，非本次引入 | 记入 `deferred-work.md`，不打断主线 |
| `reject` | 误报 | 静默丢弃 |

**处理顺序：** 先处理 intent_gap 和 bad_spec（代码会被重推），再处理 patch。

**循环回退：** 审查不通过 → 退回 implementer 修复 → 重新审查，最多 3 轮。超限后审查终止，报错人工介入。

**超时降级：** 任何 agent 超时 → 自动重试最多 3 次 → 仍失败 → 审查终止。

**配置：**
```toml
[review]
strictness = "normal"    # low/normal/high
max_findings = 20
```

---

### `/animus-status` — 状态看板

**原理：** 读取 features.json，统计任务状态分布，按优先级排序输出每个任务明细，底部推荐下一步命令。

**输出格式：**
```
======================================================
  Animus — 任务状态报告
======================================================
  统计概览
  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  总任务数  : 7
  已通过    : 4
  进行中    : 1
  待办事项  : 2

  任务明细
  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  [RUN ] [T004] 数据导出模块 (in_progress)
  [PEND] [T005] 邮件通知服务 (pending)
  ...

======================================================
  ✨ 推荐下一步：/animus-dev — 有进行中的任务，继续实施
```

**推荐规则（按优先级）：**
1. 有 in_progress → 继续实施
2. 有 failed → 修复重试
3. 有 pending → 开始新任务
4. 有 passed 未完成 → 需要审查
5. 全部 passed 完成 → 归档迭代

---

### `/animus-help` — 帮助与导航

**原理：** 读取 `.claude/animus/` 目录状态，根据当前进度推荐最合适的命令。不需要记忆命令顺序，跟着推荐走即可。

**推荐规则：**

| 当前状态 | 推荐命令 |
|---------|---------|
| 无 features.json | `/animus-setup` |
| features.json 无任务 | `/animus-dev` |
| 有进行中任务 | `/animus-dev` 继续 |
| 有完成未审查 | `/animus-review` |
| 全部完成 | `/animus-archive` |

---

### `/animus-setup` — 项目初始化

**原理：** 检测目标项目的技术栈类型（CMakeList.txt → cpp-qt/cpp-cmake、Cargo.toml → rust、go.mod → go、package.json → node、pyproject.toml → python），创建 `.claude/animus/` 运行时目录，写入默认配置。

**执行内容：**
1. 检测项目根目录
2. 按文件列表判定语言栈
3. 创建 `.claude/animus/` 目录
4. 写入默认 `project-config.json`
5. 生成初始 `features.json`

---

### `/animus-archive` — 迭代归档

**原理：** 将当前 features.json 打包到 `archive/iter-xxx-名称/` 目录下，清空 features.json 开始新的迭代。归档目录保留完整的任务历史、审查报告和日志，可随时回溯。

**执行流程：**
1. 读取当前 features.json 的任务统计
2. 创建 `archive/iter-{编号}-{名称}/` 目录
3. 复制 features.json 到归档目录
4. 生成 `iteration-summary.md`（含任务统计明细）
5. 清空 features.json（仅保留 metadata）
6. 向 memlog 写入归档事件

**命令选项：**
```
/animus-archive                           # 交互式：输入名称
/animus-archive --name "迭代 3-UI重构"     # 直接归档
```

---

### `/animus-config` — 配置管理

**原理：** 读取 `.claude/animus/config.toml`，与硬编码默认值合并，输出当前生效的完整配置。也可校验配置文件合法性。

**命令选项：**
```
/animus-config              # 显示当前配置
/animus-config --validate   # 校验配置合法性
```

**输出示例：**
```
animus 配置（两层覆盖结果）
==============================
[dev]
  default_path = auto
  autonomous = false

[review]
  strictness = normal
  max_findings = 20

[gates]
  require_task_before_write = true
...
```

---

## 五路开发路由

```
用户输入 → AI 检测意图类型
  ├── bug 报告/异常 → debug-path（3 问调试专用）
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
| `[dev]` | `default_path` | 默认路径（auto/fast/light/full） |
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
