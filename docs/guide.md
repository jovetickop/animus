# Animus 详细指南

> 本指南包含架构说明、命令详解、配置项、扩展开发等内容。

---

## 目录

1. [架构总览](#1-架构总览)
2. [命令详解](#2-命令详解)
3. [配置系统](#3-配置系统)
4. [状态机](#4-状态机)
5. [Memlog 事件源](#5-memlog-事件源)
6. [引擎 CLI](#6-引擎-cli)
7. [测试](#7-测试)
8. [审查门控](#8-审查门控)
9. [Agent 体系](#9-agent-体系)
10. [钩子系统](#10-钩子系统)
11. [安装目录结构](#11-安装目录结构)

---

## 1. 架构总览

```
插件入口 (.claude-plugin/plugin.json)
  → 编排层 (commands/*.md)
    → 引擎层 (scripts/animus-engine.py)
      → 子命令模块 (scripts/engine/*.py)
        → 持久化层 (features.json + memlog/)
        → 配置层 (config.toml 两层覆盖)
```

### 1.1 核心设计

- **状态机驱动**：任务状态流转严格校验，非法流转 exit 1
- **单一事件源**：memlog 记录所有事件，features.json 由 memlog 派生重建
- **两层配置**：defaults → config.toml
- **分层 Agent**：base/ → universal/ → {lang}/ 继承机制

---

## 2. 命令详解

### 2.1 `/animus-dev` — 统一开发入口

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

### 2.2 `/animus-review` — 代码审查

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

| 标签 | 含义 | 判定规则 | 处理 |
|------|------|---------|------|
| `intent_gap` | 意图捕获不完整 | 需求理解本身不对，代码逻辑和 spec 都偏离了用户真实意图 | 回滚 → 找用户确认意图 |
| `bad_spec` | spec 边界不够强 | 代码按 spec 写了，但 spec 没定义异常场景 | 回滚 → 修 spec → 重做 |
| `patch` | **本次改动**引入的缺陷 | 问题行在 diff 范围内（新代码/修改行） | 自动修复 |
| `defer` | **改动前已存在**的存量问题 | 问题行不在 diff 范围内（旧代码/未改动行） | 记入 `deferred-work.md`，不打断主线 |
| `reject` | 误报 | 语义误解、吹毛求疵、不符合项目实际情况 | 静默丢弃 |

**处理顺序：** 先处理 intent_gap 和 bad_spec（代码会被重推），再处理 patch。

**循环回退：** 审查不通过 → 退回 implementer 修复 → 重新审查，最多 3 轮。超限后审查终止，报错人工介入。

**超时等待：** agent 超时不等于失败。网络延迟或服务端繁忙时自动延长等待时间，继续等待不中断。仅在 agent 明确返回错误时重试（最多 3 次），仍错误则终止报错。

**配置：**
```toml
[review]
strictness = "normal"    # low/normal/high
max_findings = 20
```

---

### 2.3 `/animus-status` — 状态看板

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

### 2.4 `/animus-help` — 帮助与导航

**原理：** 读取 `.claude/animus/` 目录状态，根据当前进度推荐最合适的命令。不需要记忆命令顺序，跟着推荐走即可。

**推荐规则：**

| 当前状态 | 推荐命令 |
|---------|---------|
| 无 features.json | `/animus-init` |
| features.json 无任务 | `/animus-dev` |
| 有进行中任务 | `/animus-dev` 继续 |
| 有完成未审查 | `/animus-review` |
| 全部完成 | `/animus-archive` |

---

### 2.5 `/animus-init` — 项目初始化

**原理：** 检测目标项目的技术栈类型（CMakeList.txt → cpp-qt/cpp-cmake、Cargo.toml → rust、go.mod → go、package.json → node、pyproject.toml → python），创建 `.claude/animus/` 运行时目录，写入默认配置。

**执行内容：**
1. 检测项目根目录
2. 按文件列表判定语言栈
3. 创建 `.claude/animus/` 目录
4. 写入默认 `config.toml`（含 `[project]` 段）
5. 生成初始 `features.json`

---

### 2.6 `/animus-archive` — 迭代归档

**原理：** 将当前迭代的完整状态打包到 `archive/iter-xxx-名称/` 目录下，清空 features.json 开始新的迭代。归档目录保留完整的任务历史、memlog 事件和迭代总结，可随时回溯。

**归档内容：**

| 内容 | 去向 | 原位置处理 |
|------|------|-----------|
| features.json（含全部任务历史） | 复制到 `archive/iter-xxx/` | 清空 tasks，保留 metadata |
| memlog 所有事件 | 复制到 `archive/iter-xxx/memlog/` | 清空（新迭代从零开始） |
| iteration-summary.md（自动生成） | 创建到 `archive/iter-xxx/` | — |
| config.toml | 不变 | 保留 |
| deferred-work.md | 不归档 | 可手动移入 |

**执行流程：**
1. 读取当前 features.json 的任务统计
2. 创建 `archive/iter-{编号}-{名称}/` 目录
3. 复制 memlog/ 到归档目录，清空原目录
4. 复制 features.json 到归档目录
5. 生成 `iteration-summary.md`（含任务统计明细）
6. 清空 features.json（仅保留 metadata）

**命令选项：**
```
/animus-archive                           # 交互式：输入名称
/animus-archive --name "迭代 3-UI重构"     # 直接归档
```

### 2.7 `/animus-party` — 辩论模式

**原理：** 多 agent 并行辩论，从不同角度碰撞观点，暴露设计盲点。

**模板：**

| 模板 | 角色 | 人数 |
|------|------|------|
| `arch-review` | 架构师+审查官+测试官+构建师+规划师 | 5 |
| `code-review` | 审查官+边界猎手+验收审计官+精简审查官 | 4 |

**运行模式：** session / subagent（推荐）/ auto / agent-team

**触发方式：**
- 自动：`config.toml` 中 `[party_mode].auto_trigger` 配置
- 手动：`/animus-party`（默认）/ `/animus-party 架构评审` / `/animus-party 代码审查 session`

---

## 3. 配置系统

两层覆盖：`defaults（硬编码） ← config.toml`

文件位置：`.claude/animus/config.toml`

### 3.1 完整配置项

```toml
# animus 配置文件
# 项目根目录 .claude/animus/config.toml
# git 跟踪，团队共享
# 文件不存在时回退到硬编码默认值

[project]
# 项目类型（由 /animus-init 自动检测填入）
type = "generic"
# 构建命令
build_command = ""
# 测试命令
test_command = ""
# 运行命令
run_command = ""
# 启动时自动检查插件更新
auto_update_plugin = true

[project.verify]
# Oracle 验证门控配置
command = ""
enabled = false
timeout_seconds = 120

[dev]
# 默认行为路径：AI 自动检测时的倾向
#   auto  - AI 根据意图描述自动判断（推荐）
#   fast  - 强制 fast-path，1 句确认后直接做，适用于改动范围明确（1-2 文件）
#   light - 强制 light-path，3 问后拆任务，适用于新增功能（3-10 文件）
#   full  - 强制 full-path，走完整 7 问，适用于跨模块/架构级改动
default_path = "auto"
# 自主模式：是否跳过用户确认环节
#   false - AI 选路后先输出「将使用 XX 路径」，等待用户确认（推荐，适合有人值守）
#   true  - AI 全权决策，直接执行，不再询问用户（适合无人值守/批量任务）
autonomous = false

[review]
# 审查严格度
#   low    - 仅检查 HIGH 级问题，MEDIUM/LOW 全部通过
#   normal - 检查 HIGH + MEDIUM 级问题，LOW 自动通过（推荐）
#   high   - 所有级别问题都要求修复才能通过
strictness = "normal"
# 跳过的审查类别（数组，可多个）
#   []               - 全部检查（推荐）
#   ["naming"]       - 跳过命名规范检查
#   ["formatting"]   - 跳过代码格式检查
#   ["performance"]  - 跳过性能检查
#   ["security"]     - 跳过安全检查
#   例: ["naming", "formatting"] — 仅检查性能和安全性
skip_categories = []
# 每次审查最多输出多少条问题
#   值越小审查越精简，但可能漏掉问题；推荐 15-30
max_findings = 20

[gates]
# 写代码前必须要有 in_progress 任务
#   true  - PreToolUse hook 拦截无任务写操作，返回提示信息（推荐）
#   false - 允许直接写代码，不做拦截
require_task_before_write = true

[ponytail]
# 启用精简审查（Ponytail 原则：能删则删）
#   true  - 审查 agent 会检查过度工程、冗余抽象、死代码（推荐）
#   false - 只做功能审查，不检查精简度
enabled = true
# 文件超过此行数建议拆分
#   设为 0 表示不限制；推荐 300-800
max_lines_per_file = 500

[party_mode]
# 默认运行模式
#   session    - 同 session 内多 agent 轮流发言（适合快速辩论）
#   subagent   - 每个 agent 在独立 subagent 中运行（推荐，适合深度辩论）
#   auto       - 根据复杂度自动选择 session 或 subagent
#   agent-team - 多 agent 并行输出后汇总（适合快速达成共识）
default_mode = "subagent"
# 默认模板 ID
#   arch-review - 架构评审模板（检查模块边界、依赖方向、长期可维护性）
#   code-review - 代码审查模板（检查正确性、边界条件、验收标准、精简度）
default_party = "arch-review"
# 自动触发场景
#   ["dev-full"]            - 执行 full-path 开发时自动触发
#   ["review-controversial"] - 审查中发现争议时自动触发
#   ["dev-full", "review-controversial"] - 两者都触发（推荐）
#   []                      - 不自动触发，仅手动调用
auto_trigger = ["dev-full", "review-controversial"]
# 触发前是否询问用户
#   true  - 触发前输出「检测到 XX，是否启动辩论？」让用户选择（推荐）
#   false - 自动开始辩论
ask_before_start = true
# 最大辩论轮数
#   设 1-3 轮快速收敛，5+ 适合深度讨论。超过此轮数自动终止输出结论
max_rounds = 3
```

### 3.2 覆盖规则

文件不存在时回退硬编码默认值。配置中只写需要覆盖的段和字段，其余自动回退默认值。

---

## 4. 状态机

### 4.1 状态流转

```
pending → in_progress → passed → completed
                    ↘ failed → in_progress/pending
```

- `pending → in_progress`：前置依赖全部 passed（如果有）
- `in_progress → passed`：通过 Oracle 验证门控（verify_command）
- `in_progress → failed`：必须提供原因
- `failed → in_progress`：重试
- `completed`：终态（可重入 in_progress）

### 4.2 限制

- 同时只能有一个 `in_progress` 任务
- `depends_on` 构建 DAG，只能依赖直接前置任务
- 非法流转 `exit 1`

### 4.3 CLI 使用

```bash
python animus-engine.py transition T001 in_progress
python animus-engine.py transition T001 passed --evidence "test all pass"
```

---

## 5. Memlog 事件源

### 5.1 目录结构

```
.claude/animus/memlog/
├── 2026-07-04-1001-创建任务-T003-添加PDF导出功能.md
├── 2026-07-04-1030-状态变更-T003-进行中.md
├── 2026-07-04-1100-决策-选择QProcess作为后端.md
├── 2026-07-04-1130-归档-迭代003.md
├── 2026-07-04-1400-辩论-架构评审-T003.md
└── ...
```

### 5.2 事件类型

| 类型 | 说明 |
|------|------|
| 创建任务 | 任务创建时写入 |
| 状态变更 | 状态流转时写入 |
| 决策 | 技术/架构决策时写入 |
| 交接 | 记录交接时刻（traceability） |
| 归档 | 归档迭代时写入 |
| 辩论 | Party Mode 辩论全量日志 |

### 5.3 核心原则

- **append-only**：memlog 永不删除、永不归档
- **单一事件源**：features.json 由 memlog 派生，可删除重建
- **重建命令**：`python animus-engine.py rebuild`

---

## 6. 引擎 CLI

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

### 6.1 其他脚本

| 脚本 | 功能 |
|------|------|
| `scripts/animus_init.py` | 项目初始化（类型检测/创建目录/写配置） |
| `scripts/deferred_work.py` | deferred-work 管理（read/append/clear） |
| `scripts/memlog.py` | memlog 事件写入 |

---

## 7. 测试

192 个单元测试，全部 Python 2/3 兼容，使用 tempfile 隔离文件系统。

| 测试文件 | 覆盖 | 用例 |
|----------|------|------|
| `tests/test_config_loader.py` | 配置加载（默认值/合并/校验/兼容） | 34 |
| `tests/test_engine.py` | 状态机流转/校验/DAG 检测 | 23 |
| `tests/test_engine_extras.py` | 推荐引擎/归档/重建/memlog | 12 |
| `tests/test_deferred_work.py` | deferred-work 读写/清空/Unicode | 10 |
| `tests/test_hooks.py` | write-gate/pre-tool-use/pre-compact/stop-check/clang-format | 26 |
| `tests/test_templates.py` | task_helpers/git_helper/report_generator/coding_session/init | 71 |
| `tests/test_animus_init.py` | 项目类型检测/TOML 生成/目录创建/不覆盖 | 16 |

运行：`python -m pytest tests/`

---

## 8. 审查门控

| 门控 | 级别 | 说明 |
|------|------|------|
| Write 前门控 | HARD | 无 in_progress 任务时拒绝 Write/Edit |
| Oracle 验证 | HARD | to=passed 时执行 verify_command |
| 并行审查 | HARD | 4 agent 审查，high 阻塞 |
| 循环回退 | HARD | 最多 3 轮，超限终止 |
| 超时等待 | SOFT | 超时自动延长等待，不中断；仅报错重试 3 次 |
| SPEC 法则 | SOFT | 4 条法则校验，违规警告 |

---

## 9. Agent 体系

### 9.1 分组

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

### 9.2 命名规则

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

## 10. 钩子系统

| 钩子 | 触发时机 | 作用 | 超时 |
|------|---------|------|------|
| PreToolUse | Write/Edit 前 | write-gate 门控 + 备份 features.json + GBK→UTF-8 | 5s + 10s |
| PostToolUse | Write/Edit 后 | clang-format + format-all 多语言格式化 + UTF-8→GBK | 10s + 15s |
| PreCompact | 上下文压缩前 | JSONL compact 事件 + 状态看板同步 | 10s |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 | 10s |

优先级：bash → Python → exit 0（失败安全不阻塞主流程）。

---

## 11. 安装目录结构

```
项目根目录/
├── .claude/
│   └── animus/
│       ├── config.toml           # 配置（git 跟踪）
│       ├── features.json         # 任务状态（由 memlog 派生）
│       ├── memlog/               # 事件源目录
│       └── archive/              # 归档目录
├── .claude-plugin/
│   └── plugin.json               # 插件清单
├── commands/                     # 斜杠命令
├── agents/                       # Agent 定义
├── hooks/                        # 运行时钩子（Python 版）
│   └── scripts/
│       ├── write-gate.py         # 写代码门控拦截
│       ├── pre-tool-use.py       # 备份 + 编码转码
│       ├── clang-format.py       # C++ 格式化 + GBK 转码
│       ├── pre-compact.py        # 状态同步
│       ├── stop-check.py         # 会话结束检查
│       └── encoding-bridge.py    # GBK↔UTF-8 桥接
├── scripts/                      # Python 引擎脚本
│   ├── animus-engine.py          # 统一 CLI 入口
│   ├── animus_init.py            # 项目初始化
│   ├── engine/                   # 子命令模块
│   │   ├── cmd_status.py         # 状态看板
│   │   ├── cmd_transition.py     # 状态机流转
│   │   ├── cmd_validate.py       # 校验
│   │   ├── cmd_archive.py        # 归档
│   │   └── cmd_rebuild.py        # memlog 重建
│   ├── config_loader.py          # 配置加载器
│   ├── deferred_work.py          # deferred-work 管理
│   └── memlog.py                 # 事件源写入
├── tests/                        # 192 个单元测试
│   ├── test_config_loader.py     # 配置测试
│   ├── test_engine.py            # 状态机测试
│   ├── test_engine_extras.py     # 扩展功能测试
│   ├── test_deferred_work.py     # deferred-work 测试
│   ├── test_hooks.py             # 钩子模块测试
│   ├── test_templates.py         # 模板模块测试
│   └── test_animus_init.py       # 初始化测试
└── skills/                       # 技能定义
    ├── party-mode/               # 辩论模式
    └── brainstorming/            # 头脑风暴
```
