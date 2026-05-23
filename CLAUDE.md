# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

`CodeHarness` 是一个插件化的长任务开发工作流资产仓库，供 Claude Code 在各种类型项目中使用（C++/Qt、Python、Node.js、Rust 等）。本仓库本身**不包含业务源代码**，而是提供一套按技术栈分组、可复用的工作流资产（agents、commands、rules、hooks、templates），通过 `.claude/` 目录注入目标工程。

核心设计原则：
- **配置即代码**：用工程化配置解决 AI 长任务的失控问题。
- **状态化执行**：每个任务绑定严格的状态流转（pending → in_progress → passed/failed）与验证闭环。
- **插件化架构**：按项目类型（qt / python / node / rust）分组资产，`/code-setup` 自动检测并接入对应插件。

## 使用方式

1. 将本仓库 `.claude/` 目录复制到目标仓库根目录
2. 在目标仓库启动 Claude Code
3. 执行 `/code-setup` 初始化（自动检测项目类型，接入对应插件资产）
4. 后续开发流程：`/code-plan`（简单任务直接规划，复杂任务先准备 PRD+方案） → 依次实现任务 → `/code-check` 验收

## 架构总览

### 1. Agents（智能体角色）

位于 `.claude/agents/`，按目录分组：

| 目录 | Agent | 职责 | 适用场景 |
|------|-------|------|----------|
| **universal/** | `feature-planner` | 将 PRD/需求拆解为 harness 任务列表 | 开发启动前规划（所有项目） |
| | `task-implementer` | 单个 harness 任务的最小闭环实现 | 日常编码实现（所有项目） |
| | `test-engineer` | 测试方案设计与 test_command 补全 | 测试不足、边界用例（所有项目） |
| | `build-doctor` | 构建问题诊断 | 构建失败排查（所有项目） |
| | `code-reviewer` | 代码审查 | 代码质量把关 |
| **qt/** | `architect` | C++/Qt 方案设计与风险拆解 | 复杂功能、重构前设计 |
| | `task-implementer` | Qt 专用实现 | Qt 编码任务 |
| | `test-engineer` | Qt 测试方案 | Qt 测试 |
| | `ui-reviewer` | Qt 桌面 UI 可用性与交互质量审查 | UI 改动审查 |
| **python/** | `architect` | Python 方案设计 | Python 项目架构 |
| | `test-engineer` | Python 测试方案 | Python 测试 |
| **node/** | `architect` | Node.js 方案设计 | Node.js 项目架构 |
| | `test-engineer` | Node.js 测试方案 | Node.js 测试 |
| | `ui-reviewer` | Web UI 交互质量审查 | Web UI 改动 |
| **rust/** | `architect` | Rust 方案设计 | Rust 项目架构 |
| | `test-engineer` | Rust 测试方案 | Rust 测试 |

### 2. Commands（斜杠命令）

位于 `.claude/commands/`：

- **`/code-setup`** — 检测项目类型并接入对应插件。自动探测项目技术栈（C++/Qt、Python、Node.js、Rust），复制对应插件资产。
- **`/code-plan`** — 将 PRD 或需求转为 features.json 任务列表，每个任务包含验收标准和 test_command。
- **`/code-check`** — 围绕当前任务执行验收检查：构建正确性、测试覆盖、项目风险、UI 质量。

### 3. Rules（研发规范）

位于 `.claude/rules/`，按目录分组：

| 目录 | 规则文件 | 覆盖内容 |
|------|----------|---------|
| **universal/** | `coding-style.md` | 通用命名、文件组织、注释、格式等编码规范 |
| | `testing.md` | 通用测试基线要求、验证命令、任务通过规则 |
| | `git-workflow.md` | Commit 格式（Conventional Commits）、分支与变更约束 |
| **qt/** | `best-practices.md` | QObject 所有权、信号槽、UI/资源、工程约束 |
| | `ui-architecture.md` | 布局优先、对话框/面板边界、按钮与反馈、尺寸策略 |
| **python/** | `best-practices.md` | Python 最佳实践 |
| **node/** | `best-practices.md` | Node.js 最佳实践 |
| **rust/** | `best-practices.md` | Rust 最佳实践 |

### 4. Hooks（自动化钩子）

位于 `.claude/hooks/`，通过 `hooks.json` 配置 PreToolUse / PostToolUse 钩子。当前启用：
- **PostToolUse**（Write/Edit 后）：自动对 `.cpp/.h/.hpp` 等文件执行 `clang-format`（PS1/Bash 双后备）

### 5. Templates（初始化模板）

位于 `.claude/templates/`，供 `/code-setup` 使用的资产：

- **`CLAUDE.md`** — 目标工程的根 CLAUDE.md 模板，包含会话初始化、状态流转、开发与验收、Git 提交等 MUST 规则
- **`.clang-format`** — C++ 代码格式化配置
- **`.mcp.json`** — MCP 工具配置
- **`existing_project/`** — 通用存量工程接入模板（CLAUDE.md、review-checklist.md、cmake-adapter.md）
- **`harness/`** — 长任务自动化执行资产

### 6. Harness（长任务状态管理）

模板目录 `.claude/templates/harness/`，初始化后变为 `.claude/harness/`：

| 文件 | 用途 |
|------|------|
| `features.json` | 任务清单与状态（id, name, status, depends_on, priority, test_command, acceptance_criteria） |
| `claude-progress.txt` | 进度日志（每次操作追加） |
| `update-progress.ps1` / `.bat` | 状态流转与报告更新 |
| `coding-session.ps1` / `.bat` | 会话入口（状态扫描） |
| `run-regression.ps1` | 构建 + 回归测试 |
| `init.ps1` / `.bat` | 初始化 harness 环境 |
| `show-status.py` | 可执行与失败任务概览 |

## 核心工作流

每次编码会话的标准流程：

1. **会话初始化** — 执行 `coding-session.ps1`、`show-status.py` 了解当前进度
2. **检查任务状态** — 优先续做 `in_progress` 任务，或选择下一个 `pending` 任务
3. **开始任务** — `update-progress.ps1 <TaskId> in_progress "说明"`
4. **实现** — 使用对应 agent 完成最小闭环
5. **验证** — 按 `/code-setup` 自动探测的命令执行构建和测试
6. **验收** — 执行 `/code-check` 审查
7. **完成任务** — `update-progress.ps1 <TaskId> passed "说明"`
8. **提交** — `git add` + `git commit` + `git push`
9. **重复** — 处理下一个任务

## 本仓库无构建/测试

`CodeHarness` 本身是模板仓库，不包含业务代码，因此**无本地构建和测试命令**。它产出 `.claude/` 资产用于目标工程，由 `/code-setup` 在目标仓库中自动检测项目类型并写入对应的构建/测试命令。
