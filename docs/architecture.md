# Animus 架构文档

本文档从 CLAUDE.md 迁移而来，包含架构分层、设计模式、决策记录、运行时要求等参考性内容。

## 目录

- [语言分布](#语言分布)
- [运行时要求](#运行时要求)
- [核心框架/库](#核心框架库)
  - [代码格式化工具](#代码格式化工具)
  - [Python 运行时依赖](#python-运行时依赖)
- [配置文件体系](#配置文件体系)
- [构建系统](#构建系统)
- [平台注意事项](#平台注意事项)
- [架构分层/模块划分](#架构分层模块划分)
  - [1. 插件入口层](#1-插件入口层)
  - [2. 编排层 (Commands)](#2-编排层-commands)
  - [3. 执行层 (Agents)](#3-执行层-agents)
  - [4. 执行层 (Rules)](#4-执行层-rules)
  - [5. 运行时钩子系统 (Hooks)](#5-运行时钩子系统-hooks)
  - [6. 运行时引擎 (animus)](#6-运行时引擎-animus)
  - [7. 持久化层 (State)](#7-持久化层-state)
- [关键设计模式](#关键设计模式)
  - [1. 状态机驱动的工作流](#1-状态机驱动的工作流)
  - [2. 分层 Agent 继承](#2-分层-agent-继承)
  - [3. 模板 + 安装脚本的部署模式](#3-模板--安装脚本的部署模式)
  - [4. 钩子自动化](#4-钩子自动化)
  - [5. Oracle 验证门控](#5-oracle-验证门控)
  - [6. 跨会话恢复](#6-跨会话恢复)
- [架构决策记录（隐含的）](#架构决策记录隐含的)
- [架构质量属性](#架构质量属性)

## 语言分布

| 语言 | 占比 | 用途 |
|------|------|------|
| PowerShell | ~45% | 核心状态机引擎、项目初始化编排、会话管理、回归测试运行器、hook 脚本 |
| Python | ~30% | 状态显示、状态机替代实现、编码桥接（GBK/UTF-8）、多语言格式化分发、会话恢复、验证脚本 |
| Markdown | ~20% | Agent 定义（22 个）、插件清单（plugin.json）、编码规范规则、命令文档 |
| JSON | ~5% | 配置（hooks.json、settings.local.json、project-config.json、features.json） |
| Shell (Bash) | ~3% | 跨平台 hook 降级脚本（clang-format、pre-tool-use、pre-compact、stop-check） |
| YAML / TOML | 无 | 不在本仓库中使用 |

## 运行时要求

| 运行时 | 版本要求 | 用途 |
|--------|----------|------|
| PowerShell | 5.1+（Windows） | 主要运行时，所有 .ps1 脚本 |
| Python | 2.7+ / 3.x 双兼容 | 所有 .py 脚本，含 Python 2/3 兼容层（`from __future__`） |
| Bash | 任意 POSIX shell | 跨平台 hook 降级（.sh 脚本） |
| Node.js | 任意（通过 npx） | （可选）MCP 服务器运行时 |
| Git | 任意 | 版本控制、提交工作流 |

## 核心框架/库

### 代码格式化工具

| 工具 | 用途 | 在 format-all.py 中的优先级 |
|------|------|----------------------------|
| `black` | Python 格式化 | 首选，降级到 autopep8 |
| `autopep8` | Python 格式化 | 降级选项 |
| `prettier` | JS/TS 格式化 | 首选，降级到 eslint --fix |
| `eslint --fix` | JS/TS 格式化 | 降级选项 |
| `cargo fmt` | Rust 格式化 | 唯一选项 |
| `clang-format` | C/C++ 格式化 | 唯一选项（另有独立 .ps1/.sh hook 脚本） |

### Python 运行时依赖

- `json`, `os`, `sys`, `subprocess`, `argparse`, `datetime`, `re`, `time`, `glob`, `io`

## 配置文件体系

| 文件 | 用途 |
|------|------|
| `.claude/settings.local.json` | Claude Code 本地权限白名单（此仓库也保留在 `.claude/` 下）（Bash/Read/MCP/skill 调用） |
| `hooks/hooks.json` | 注册 PostToolUse/PreToolUse/PreCompact/Stop 四个钩子 |
| `templates/animus/project-config.json` | 目标项目类型配置（frontend/backend/verify 字段） |
| `templates/.clang-format` | C++ 格式化规则模板 |
| `.claude-plugin/plugin.json` | 插件清单，声明元信息、斜杠命令和自动发现组件 |
| `.claude/animus/config.toml` | 三层团队配置（defaults → team → user 层覆盖），控制 dev/review/party_mode 等行为 |
| `.claude/animus/config.user.toml` | 用户个人配置（gitignored），覆盖 team 层 |
| `scripts/config_loader.py` | 三层配置加载合并工具，支持 `load_config()`、`get_config_value()`、`validate_config()` |
| `.claude/animus/memlog/` | 单一事件源目录，每事件一个中文 Markdown 文件（append-only，永不删除） |
| `.gitignore` | 排除 CLAUDE.md、settings.local.json、worktrees、.codegraph/ |

## 构建系统

- CMake（含 Qt 检测）→ `cpp-qt` / `cpp-cmake`
- Cargo.toml → `rust`
- go.mod → `go`
- package.json → `node`
- pyproject.toml / requirements.txt → `python`
- 无匹配 → `generic`

## 平台注意事项

- **PowerShell 脚本用 UTF-8 编码**（CLAUDE.md 明确指出使用 UTF-8 无 BOM 编码，已修复 BOM 问题）
- **Python 脚本兼容 Python 2/3**：使用 `from __future__ import print_function, unicode_literals`，`subprocess.Popen` + `communicate()`
- **跨平台降级**：所有 hook 脚本同时提供 `.sh` 和 `.ps1` 两种版本，互为 fallback
- **GBK 编码支持**：通过 `encoding-bridge.py` 实现 GBK ↔ UTF-8 双向转换，仅作用于 C/C++ 源文件

## 架构分层/模块划分

### 1. 插件入口层

| 模块 | 职责 | 文件 |
|------|------|------|
| 插件清单 | 声明插件元信息、斜杠命令和自动发现组件 | `.claude-plugin/plugin.json` |
| 项目状态判定 | 目标项目状态判定由 `commands/animus-setup.md` 处理 | `commands/animus-setup.md` |

### 2. 编排层 (Commands)

| 命令 | 职责 | 文件 |
|------|------|------|
| `/animus-setup` | 项目初始化 + 类型检测 + 创建 `.claude/animus/` 运行时目录 | `commands/animus-setup.md` |
| `/animus-dev` | 统一开发入口（四路路由：debug/fast/light/full） | `commands/animus-dev.md` |
| ~~`/animus-plan`~~ | ~~已移除，改用 `/animus-dev --full`~~ | — |
| `/animus-review` | 通用验收 + 语言专项验收 | `commands/animus-review.md` |
| ~~`/animus-debug`~~ | ~~已移除，功能合并入 `/animus-dev` 的 debug-path~~ | — |
| ~~`/animus-handoff`~~ | ~~已移除，memlog 自动接管~~ | — |
| ~~`/animus-continue`~~ | ~~已移除，/animus-dev 自动恢复~~ | — |
| `/animus-archive` | 归档当前迭代，清空并开始新迭代 | `commands/animus-archive.md` |
| 验证辅助 | features.json 结构校验 | `commands/validate-features.ps1` |
| 一致性检查 | 检查状态文件一致性 | `commands/check-consistency.ps1` |

### 3. 执行层 (Agents)

- **`agents/base/`** — 基础核心文件，不单独使用。`task-implementer-core.md` 和 `test-engineer-core.md` 包含通用的职责定义、输出格式、边界约束。各语言专属 agent 通过 HTML 注释 (`<!-- ... -->`) 引用。
- **`agents/universal/`** — 跨语言通用 Agent，5 个：
- **`agents/{lang}/`** — 语言专属 Agent，按语言分组：

### 4. 执行层 (Rules)

- **通用**: `coding-style.md`、`testing.md`、`git-workflow.md`
- **语言**: `cpp-cmake/` (best-practices + encoding), `qt/` (best-practices + ui-architecture), `python/`, `node/`, `rust/`, `go/` (各 1 个 best-practices), `frontend/` (component-guidelines)

### 5. 运行时钩子系统 (Hooks)

| 钩子 | 触发时机 | 用途 |
|------|---------|------|
| PreToolUse | Write/Edit 前 | 备份 features.json + GBK->UTF-8 编码转换 |
| PostToolUse | Write/Edit 后 | clang-format + format-all 多语言格式化 + UTF-8->GBK 回转 |
| PreCompact | 上下文压缩前 | 刷进度（JSONL compact 事件 + features→task_plan 同步） |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 |

### 6. 运行时引擎 (animus)

- `update-progress.ps1` — 核心状态机引擎（逐步迁移到 `engine/cmd_transition.py`）
- `animus-engine.py` — 统一 CLI 入口，调度所有 engine 子命令
- `engine/` — 子命令模块目录：cmd_status.py、cmd_transition.py、cmd_validate.py、cmd_archive.py、cmd_rebuild.py
- `show-status.py` — 状态概览显示
- `run-regression.ps1` — 一键构建+测试
- `init.ps1` — 首次初始化引导
- `coding-session.ps1` — 会话入口
- `project-config.json` — 项目类型与构建命令配置
- `validate-features.ps1` — 结构校验 + 循环依赖检测 (Kahn 算法)

### 7. 持久化层 (State)

- `features.active.json` — 当前活动任务 (Token 优化分片)
- `features.archive.json` — 已完成/失败归档
- `animus-history.jsonl` — 统一结构化日志
- `memlog/` — 单一事件源目录，每事件一个中文 Markdown 文件（append-only，永不删除）
- `task_plan.md` — 子步骤追踪
- `findings.md` — 知识积累

## 关键设计模式

### 1. 状态机驱动的工作流

- 任务状态严格限定：`pending | in_progress | passed | failed | completed`
- 状态流转由 `update-progress.ps1` 强制执行，非法流转 `exit 1`
- `depends_on` 构建 DAG，只能依赖直接前置任务
- 并行组 (`parallel_group`) 支持不同组并发执行

### 2. 分层 Agent 继承

- `base/` 定义通用核心（HTML 注释引用机制）
- `universal/` 提供跨语言通用 Agent
- `{lang}/` 提供语言专属行为
- 语言专属 Agent 只保留增量差异，减少重复

### 3. 模板 + 安装脚本的部署模式

- 所有技能资产集中存储在仓库根目录下
- `init-project.ps1` 是安装脚本，为目标项目创建 `.claude/animus/` 运行时目录
- 不再修改目标项目的 CLAUDE.md

### 4. 钩子自动化

- 4 种钩子覆盖整个 Claude Code 会话生命周期
- 双平台脚本 (bash + PowerShell) 互为降级
- 失败时 `exit 0` 保证不阻塞主流程

### 5. Oracle 验证门控

- 任务标记 `passed` 前自动执行 `verify_command`
- 验证失败自动退回 `failed`，确保不可跳过

### 6. 跨会话恢复

- `session-catchup.py` 直接读文件输出 5 问恢复检查，关机/断网同效
- `task_plan.md` 子步骤追踪 + `findings.md` 知识积累
- PreCompact 钩子自动同步 features.json → task_plan.md
- 状态分片 (active/archive) 降低 Token 消耗约 78%

## 架构决策记录（隐含的）

| 决策 | 理由 | 体现位置 |
|------|------|----------|
| 所有插件资产放在仓库根目录下 | 插件源码仓库，通过 `/plugin install` 安装，路径由 `${CLAUDE_PLUGIN_ROOT}` 解析 | agents/, commands/, rules/ 等目录 |
| 使用 PowerShell 作为主脚本语言 | Windows 优先的用户群体，PS 5.1 兼容 | `templates/animus/` |
| 核心脚本从 PS 迁移到 Python | 跨平台 + Python 2/3 兼容 | `scripts/` 中的 `.py` 文件 |
| HTML 注释引用替代原生 include | Markdown 缺乏 include 机制，HTML 注释是最便携方式 | `agents/base/*.md` |
| 前置声明式 tasks.json | JSON 比 YAML 更宽泛的语言解析支持 | `templates/animus/features.json` |
| 不修改目标项目的 CLAUDE.md | 目标项目保持独立，仅创建 .claude/animus/ 运行时目录 | `init-project.ps1` |
| 状态分片 (active/archive) | 缩减 Token 消耗约 78%，长项目更友好 | `.claude/animus/` 目录 |
| 双平台钩子脚本 | Windows/Linux 开发环境都需支持 | `hooks/scripts/*.ps1 + *.sh` |
| 项目类型自动检测 | 零配置上手，按项目文件判定语言栈 | `init-project.ps1` 步骤 5 |
| 空命令值保持空 | 不硬编码默认值，由用户首次运行时填写 | `project-config.json` |

## 架构质量属性

### 可维护性

- Agent 和 Rule 按语言分组，新增语言只需新建 `agents/{lang}/` + `rules/{lang}/` 目录
- 核心逻辑在 `base/` 中，修改通用行为只需改一个文件
- 每个文件职责单一：Agent 定义、规则、命令各司其职

### 可扩展性 (插件化)

- 新增语言：创建 `agents/{lang}/` 目录 + `rules/{lang}/` 目录（安装脚本中无需添加映射，不再复制到目标项目）
- 新增 Agent：在对应目录创建 `.md` 文件，keep `description` frontmatter
- 新增钩子：在 `hooks/hooks.json` 注册，在 `hooks/scripts/` 加脚本

### 可测试性 (插件自身)

- 本仓库没有构建步骤（无 CMakeLists.txt/Cargo.toml/package.json）
- 验证通过语法检查：`PSParser` (PS) + `py_compile` (Python) + `json.tool` (JSON)
- 全语言回归测试在目标工程上执行，至少 3 种语言

### 可靠性

- Oracle 门控防止任务被过早标记完成
- 状态机校验防止非法流转
- hooks 双平台互为降级，单点失败不阻塞
- 每次状态流转生成 `.claude/animus/docs/` 报告 + 追加 JSONL 日志

### 跨会话持久性

- `features.active.json` + `features.archive.json` 持久化任务状态
- `animus-history.jsonl` 记录所有状态转换历史（JSONL 格式，追加写入）
- `session-catchup.py` 在会话中断后自动恢复（5 问重启检查）
- `findings.md` 记录决策和错误经验（非易失性知识）

### 性能考量

- 状态分片 (active/archive) 减少每次加载的 Token 量（约 78%）
- Hook timeout 限制 (PreToolUse/PostToolUse: 10s, PostToolUse format-all: 15s)
- `parallel_group` 支持并行任务执行
