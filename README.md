# animus

状态机驱动的 AI 编码工作流引擎 — Claude Code 插件。

任务拆解编排、进度持久化、跨会话恢复、自动审查门控。让 AI 辅助的编码工作**可跟踪、可验证、可重复**。

---

## 安装

```
/plugin marketplace add jovetickop/animus
/plugin install animus@animus

# 在目标项目中初始化
/animus-init
```

---

## 核心能力

### 状态机驱动的工作流

```
pending → in_progress → passed → completed
                    ↘ failed → in_progress/pending
```

- 严格的状态流转校验，非法流转 `exit 1`
- `depends_on` DAG 依赖管理，自动阻塞前置任务
- Oracle 验证门控：`passed` 前必须执行 verify_command
- 并行组 (`parallel_group`) 支持并发任务

### 25+ 多语言 Agent

| 语言 | Agent |
|------|-------|
| 通用 (universal) | 规划师、实现者、测试官、构建师、审查官、边界猎手、验收审计官、精简审查官 |
| C++/Qt | 架构师、实现者、测试官、UI 审查官 |
| C++/CMake | 架构师 |
| Python | 架构师、测试官 |
| Node/Web | 架构师、测试官、UI 审查官 |
| Rust | 架构师、测试官 |
| Go | 架构师、测试官 |
| Frontend | 规划师（前端补充） |

每个 Agent 激活后展示**编号菜单**（1 2 3 4），意图明确时自动跳过菜单直接执行。

### 四路开发路由 `/animus-dev`

| 路径 | 适用场景 | 流程 |
|------|---------|------|
| **debug** | Bug 报告、异常 | 3 问定位 → features.json → 实现 → 审查 |
| **fast** | 1-2 文件小改动 | 1 句确认 → 直接实现 → 审查 |
| **light** | 3-10 文件新增功能 | 3 问 → 拆任务 → 实现 → 审查 |
| **full** | 跨模块、架构改动 | 7 问 + 可选脑暴 → 拆任务队列 → 实现 → 审查 |

### 四 Agent 并行审查 `/animus-review`

| Agent | 审查维度 | 严重度门控 |
|-------|---------|-----------|
| 审查官 | 正确性、安全、竞态 | HIGH 阻塞、MEDIUM 确认、LOW 通过 |
| 边界猎手 | 空值、溢出、并发、资源泄露 | |
| 验收审计官 | 逐条核对 spec.success | 循环回退最多 3 轮 |
| 精简审查官 | 过度工程、可删减抽象 | 超限终止，人工介入 |

### Memlog 事件源

- **Append-only**：所有事件（创建任务、状态变更、决策、归档、辩论）只追加不修改
- **单一事件源**：features.json 由 memlog 派生，可 `rebuild` 重建
- **灾难恢复**：`session-catchup.py` 自动 5 问恢复，断网/关机同效

### 辩论模式 `/animus-party`

多 Agent 并行辩论，支持架构评审和代码审查两种预装模板。
自动触发：在 `--full` 路径开发或审查争议时自动启动。

### 运行时钩子

| 钩子 | 触发时机 | 作用 |
|------|---------|------|
| PreToolUse | Write/Edit 前 | 门控拦截 + 自动备份 features.json（保留最近 5 个） |
| PostToolUse | Write/Edit 后 | clang-format + 多语言格式化 + GBK↔UTF-8 编码桥接 |
| PreCompact | 上下文压缩前 | 刷进度 + memlog 事件写入 + append-only 检测 |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 |

纯 Python 实现，兼容 2/3，无需 `jq` 等外部工具。

### 技能

| 技能 | 用途 |
|------|------|
| 辩论模式 | 架构评审/代码审查（含预装模板） |
| 头脑风暴 | 6 个技法（PRFAQ/第一性原理/SCAMPER/逆向思维/坏人测试/竞品评测） |
| 系统性调试 | Bug 系统化修复流程（根因调查→模式分析→假设验证→实施修复） |
| TDD 工作流 | 测试驱动开发（红→绿→重构） |

### 双模式插件验证器

```bash
python scripts/plugin-validator.py            # 8 条确定性规则
python scripts/plugin-validator.py --json     # JSON 输出
python scripts/plugin-validator.py --strict   # CI 严格模式
python scripts/plugin-validator.py --fix      # 自动修复
```

确定性规则（R1-R8）检查插件结构完整性，语义规则（S1-S8）供 AI 做质量审查。

---

## 命令一览

| 命令 | 用途 |
|------|------|
| `/animus-init` | 项目初始化（自动检测语言栈） |
| `/animus-dev` | 统一开发入口（四路路由） |
| `/animus-review` | 代码审查（4 agent 并行） |
| `/animus-party` | 辩论模式 |
| `/animus-status` | 状态看板 + 推荐下一步 |
| `/animus-help` | 帮助与导航 |
| `/animus-archive` | 迭代归档 |

### 引擎 CLI

```bash
python scripts/animus-engine.py status                  # 显示状态
python scripts/animus-engine.py transition T001 passed  # 状态流转
python scripts/animus-engine.py validate                # 校验 features.json
python scripts/animus-engine.py validate --plugin       # 校验插件完整性
python scripts/animus-engine.py archive --name "v1.5"   # 归档
python scripts/animus-engine.py rebuild                 # 从 memlog 重建
```

---

## 配置

`.claude/animus/config.json` — 两层覆盖（默认值 ← 配置文件），零第三方库依赖。

```json
{
  "dev": { "default_path": "auto", "autonomous": false },
  "review": { "strictness": "normal", "max_findings": 20 },
  "gates": { "require_task_before_write": true }
}
```

详见 `docs/reference/config-options.md`。

---

## 质量

- **344+ 单元测试**，全部通过
- Python 2.7+ / 3.x 双兼容
- 跨平台（Windows/Linux/macOS）
- 所有钩子失败 `exit 0` 不阻塞主流程
- 插件自检：`python scripts/plugin-validator.py --strict`

---

## 文档导航

| 读者 | 入口 |
|------|------|
| 新用户 | [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md) |
| 命令参考 | [`docs/reference/commands.md`](docs/reference/commands.md) |
| 配置项 | [`docs/reference/config-options.md`](docs/reference/config-options.md) |
| Agent 索引 | [`docs/agent-index.md`](docs/agent-index.md) |
| 架构设计 | [`docs/explanation/architecture.md`](docs/explanation/architecture.md) |
| 状态机原理 | [`docs/explanation/state-machine.md`](docs/explanation/state-machine.md) |
| 路线图 | [`docs/reference/bmad-optimization-roadmap.md`](docs/reference/bmad-optimization-roadmap.md) |
| 全部文档 | [`docs/README.md`](docs/README.md) |
