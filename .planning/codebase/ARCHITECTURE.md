# 架构分析
_生成日期：2026-06-14_

## 总体架构概览

`harness-cc` 是一个 Claude Code **技能插件式的编码工作流引擎**，采用 **微内核 + 插件** 风格架构。核心层提供状态机引擎和运行时钩子，语言专属插件通过 Agent 定义和编码规则扩展支持 6 种语言生态（C++/Qt、C++/CMake、Python、Node.js、Rust、Go）。

```text
┌─────────────────────────────────────────────────────────────────────┐
│                     技能入口层 (Skill Entry)                          │
│                     SKILL.md  (/harness-cc 激活)                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     编排层 (Orchestration Layer)                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  harness-code-   │  │ harness-code-   │  │  harness-code-      │  │
│  │  setup           │  │ plan            │  │  review             │  │
│  │  初始化 + 检测    │  │ PRD -> features │  │  通用 + 专项验收     │  │
│  │  .claude/commands/│  │ .claude/commands/│  │ .claude/commands/  │  │
│  │  harness-code-   │  │ harness-code-   │  │  harness-code-      │  │
│  │  setup.md/.ps1   │  │ plan.md         │  │  review.md          │  │
│  └────────┬─────────┘  └────────┬────────┘  └─────────┬───────────┘  │
└───────────┼────────────────────┼──────────────────────┼──────────────┘
            │                    │                      │
            ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     执行层 (Execution Layer)                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Agents (Agent 定义, 23 个 .md 文件)                           │   │
│  │  ┌──────────┐  ┌────────────────┐  ┌──────────────────────┐  │   │
│  │  │ base/    │  │  universal/    │  │  {lang}/ (6种语言)     │  │   │
│  │  │ 核心引用  │  │  通用 5 Agent  │  │  语言专属 Agent        │  │   │
│  │  └──────────┘  └────────────────┘  └──────────────────────┘  │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │  Rules (编码规范, 12 个 .md 文件)                               │   │
│  │  universal/ + cpp-cmake/ + qt/ + python/ + node/ + rust/ + go/│   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     运行时引擎 + 持久化层                              │
│  ┌─────────────────────┐  ┌─────────────────────────────────────┐   │
│  │ Harness 状态引擎      │  │ State 持久化                        │   │
│  │ .claude/harness/    │  │ .claude/state/                      │   │
│  │ update-progress.ps1 │  │ features.active.json                │   │
│  │ show-status.py      │  │ features.archive.json               │   │
│  │ run-regression.ps1  │  │ claude-progress.txt                 │   │
│  │ project-config.json │  │ harness-history.jsonl               │   │
│  └─────────────────────┘  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## 架构分层/模块划分

### 1. 技能入口层

| 模块 | 职责 | 文件 |
|------|------|------|
| 技能激活 | `/harness-cc` 命令触发，检测项目状态 | `SKILL.md` |
| 项目状态判定 | 判断目标项目是否已初始化，引导进入不同分支 | `SKILL.md` |

### 2. 编排层 (Commands)

| 命令 | 职责 | 文件 |
|------|------|------|
| `/harness-code-setup` | 项目初始化 + 类型检测 + 资产复制 + CLAUDE.md 合并 | `.claude/commands/harness-code-setup.md` |
| `/harness-code-plan` | PRD/方案文档 -> features.json 任务列表 | `.claude/commands/harness-code-plan.md` |
| `/harness-code-review` | 通用验收 + 语言专项验收 | `.claude/commands/harness-code-review.md` |
| 验证辅助 | features.json 结构校验 | `.claude/commands/validate-features.ps1` |
| 一致性检查 | 检查状态文件一致性 | `.claude/commands/check-consistency.ps1` |

### 3. 执行层 (Agents)

Agent 体系采用 **分层继承** 结构：

- **`agents/base/`** — 基础核心文件，不单独使用。`task-implementer-core.md` 和 `test-engineer-core.md` 包含通用的职责定义、输出格式、边界约束。各语言专属 agent 通过 HTML 注释 (`<!-- ... -->`) 引用。
- **`agents/universal/`** — 跨语言通用 Agent，5 个：
  - `feature-planner.md` — PRD/方案 -> 任务拆解 (23 个 Agent 定义文件中最重的规划 Agent)
  - `task-implementer.md` — 通用单任务最小闭环实现
  - `test-engineer.md` — 通用测试设计
  - `build-doctor.md` — 构建诊断（支持 Web 搜索）
  - `code-reviewer.md` — 通用代码审查
- **`agents/{lang}/`** — 语言专属 Agent，按语言分组：
  - `qt/` — 4 个 (architect/task-implementer/test-engineer/ui-reviewer)
  - `cpp-cmake/` — 1 个 (architect，其余用 universal)
  - `python/` — 2 个 (architect/test-engineer)
  - `node/` — 3 个 (architect/test-engineer/ui-reviewer)
  - `rust/` — 2 个 (architect/test-engineer)
  - `go/` — 2 个 (architect/test-engineer)
  - `frontend/` — 1 个 (feature-planner-frontend，被 universal/feature-planner.md 引用)

### 4. 执行层 (Rules)

12 个规范文件，按 `universal/` (通用 3 个) + 各语言专属 (9 个) 组织：
- **通用**: `coding-style.md`、`testing.md`、`git-workflow.md`
- **语言**: `cpp-cmake/` (best-practices + encoding), `qt/` (best-practices + ui-architecture), `python/`, `node/`, `rust/`, `go/` (各 1 个 best-practices), `frontend/` (component-guidelines)

### 5. 运行时钩子系统 (Hooks)

4 种自动化钩子，注册在 `.claude/hooks/hooks.json`：

| 钩子 | 触发时机 | 用途 |
|------|---------|------|
| PreToolUse | Write/Edit 前 | 备份 features.json + GBK->UTF-8 编码转换 |
| PostToolUse | Write/Edit 后 | clang-format + format-all 多语言格式化 + UTF-8->GBK 回转 |
| PreCompact | 上下文压缩前 | 刷写进度到 claude-progress.txt |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 |

所有钩子脚本同时提供 `.ps1` (Windows) 和 `.sh` (Linux/macOS) 双版本，互为降级。

### 6. 运行时引擎 (Harness)

目标项目 `.claude/harness/` 中的状态管理脚本：
- `update-progress.ps1` — 核心状态机引擎，执行状态流转校验、Oracle 验证门控
- `show-status.py` — 状态概览显示
- `run-regression.ps1` — 一键构建+测试
- `init.ps1` — 首次初始化引导
- `coding-session.ps1` — 会话入口
- `project-config.json` — 项目类型与构建命令配置
- `validate-features.ps1` — 结构校验 + 循环依赖检测 (Kahn 算法)

### 7. 持久化层 (State)

- `features.active.json` — 当前活动任务 (Token 优化分片)
- `features.archive.json` — 已完成/失败归档
- `claude-progress.txt` — 累计进度日志
- `harness-history.jsonl` — 失败历史分析

## 核心数据流

### 主工作流 (8 步闭环)

```
/harness-cc 激活
     │
     ▼
Step 1: 读取状态 ────→ read features.active.json + claude-progress.txt
     │
     ▼
Step 2: 选择任务 ─────→ in_progress > pending(depends_on已满足, priority最高)
     │                      │
     │              ┌───────┘ (无任务时)
     │              ▼
     │       /harness-code-plan ──→ feature-planner agent ──→ 生成 features.json
     │
     ▼
Step 3: 标记开始 ────→ update-progress.ps1 <TaskId> in_progress
     │
     ▼
Step 4: 实现 ────────→ 按 project-type 选择语言 agent 实现
     │                   │ 构建失败 → build-doctor agent
     │                   │ UI改动 → ui-reviewer agent
     ▼
Step 5: 代码审查 ─────→ code-reviewer agent (critical/high 必须修复)
     │
     ▼
Step 6: 验证 ────────→ 执行 build-command + test_command
     │                   run-regression.ps1 一键执行
     ▼
Step 7: 验收 ────────→ /harness-code-review (通用+语言专项)
     │
     ▼
Step 8: 完成/失败 ────→ update-progress.ps1 <TaskId> passed/failed
                         │ passed → git commit
                         │ failed → 记录原因, 退回 pending 或重试
     │
     └──→ 回到 Step 1 (循环直到无任务)
```

### 状态机流转

```
                ┌─────────────────┐
                │    pending      │
                └────────┬────────┘
                         │ depends_on 全部 passed
                         ▼
                ┌─────────────────┐
          ┌─────│   in_progress    │◄────┐
          │     └────────┬────────┘     │
          │              │              │
          │     ┌────────┴────────┐     │
          │     │                │      │
          │     ▼                ▼      │
          │ ┌──────────┐  ┌──────────┐  │
          │ │  passed  │  │  failed  │──┘
          │ └─────┬────┘  └──────────┘  (重试)
          │       │
          │       ▼
          │ ┌──────────────┐
          │ │  completed   │
          │ │  (passed 别名) │
          │ └──────────────┘
          │
          └──→ 回到 pending (人工重排时)
```

### 初始化数据流

```
init-project.ps1 执行
     │
     ├── Step 1: 确定 SKILL.md 所在目录
     ├── Step 2: 检查已有初始化状态
     ├── Step 3: 创建 .claude/ 目录结构
     ├── Step 4: 复制 harness/ 状态引擎模板
     ├── Step 5: 检测项目类型 (CMake > Qt > Cargo > go.mod > package.json > pyproject.toml)
     ├── Step 6: 复制通用资产 (universal agents + universal rules + commands + hooks)
     ├── Step 7: 复制语言专项资产 (按检测类型)
     ├── Step 8: 复制根目录配置文件 (.clang-format, .mcp.json, review-checklist.md,...)
     ├── Step 9: CLAUDE.md 合并 (追加式, 哨兵标记)
     └── Step 10: 更新 project-config.json

完成 → /harness-code-plan → 工作流
```

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
- 所有运行时资产集中存储在 `templates/` 下
- `init-project.ps1` 是单入口安装脚本，负责检测、复制、合并
- CLAUDE.md 采用哨兵标记的追加式合并，而非覆盖

### 4. 钩子自动化
- 4 种钩子覆盖整个 Claude Code 会话生命周期
- 双平台脚本 (bash + PowerShell) 互为降级
- 失败时 `exit 0` 保证不阻塞主流程

### 5. Oracle 验证门控
- 任务标记 `passed` 前自动执行 `verify_command`
- 验证失败自动退回 `failed`，确保不可跳过

### 6. 跨会话恢复
- `session-catchup.py` 在 `/clear` 后自动重建上下文
- 状态持久化为 `features.active.json` (分片) 降低 Token 消耗约 78%

## 架构决策记录（隐含的）

| 决策 | 理由 | 体现位置 |
|------|------|----------|
| 所有技能资产放在 `.claude/` 下 | 符合 Claude Code 插件约定，单一复制源 | 仓库根结构 |
| 使用 PowerShell 作为主脚本语言 | Windows 优先的用户群体，PS 5.1 兼容 | `templates/harness/` |
| 核心脚本从 PS 迁移到 Python | 跨平台 + Python 2/3 兼容 | `scripts/` 中的 `.py` 文件 |
| HTML 注释引用替代原生 include | Markdown 缺乏 include 机制，HTML 注释是最便携方式 | `agents/base/*.md` |
| 前置声明式 tasks.json | JSON 比 YAML 更宽泛的语言解析支持 | `templates/state/features.json` |
| CLAUDE.md 追加而非覆盖 | 目标项目已有自己的 CLAUDE.md，不能破坏 | `init-project.ps1` 步骤 9 |
| 状态分片 (active/archive) | 缩减 Token 消耗约 78%，长项目更友好 | `state/` 目录 |
| 双平台钩子脚本 | Windows/Linux 开发环境都需支持 | `hooks/scripts/*.ps1 + *.sh` |
| 项目类型自动检测 | 零配置上手，按项目文件判定语言栈 | `init-project.ps1` 步骤 5 |
| 空命令值保持空 | 不硬编码默认值，由用户首次运行时填写 | `project-config.json` |

## 架构质量属性

### 可维护性
- Agent 和 Rule 按语言分组，新增语言只需新建 `agents/{lang}/` + `rules/{lang}/` 目录
- 核心逻辑在 `base/` 中，修改通用行为只需改一个文件
- 每个文件职责单一：Agent 定义、规则、命令各司其职

### 可扩展性 (插件化)
- 新增语言：创建 `agents/{lang}/` 目录 + `rules/{lang}/` 目录 + 在 `init-project.ps1` `$TypeMapping` 添加映射
- 新增 Agent：在对应目录创建 `.md` 文件，keep `description` frontmatter
- 新增钩子：在 `hooks/hooks.json` 注册，在 `hooks/scripts/` 加脚本
- MCP 集成：通过 `.mcp.json` 模板，非侵入式

### 可测试性 (插件自身)
- 本仓库没有构建步骤（无 CMakeLists.txt/Cargo.toml/package.json）
- 验证通过语法检查：`PSParser` (PS) + `py_compile` (Python) + `json.tool` (JSON)
- 全语言回归测试在目标工程上执行，至少 3 种语言

### 可靠性
- Oracle 门控防止任务被过早标记完成
- 状态机校验防止非法流转
- hooks 双平台互为降级，单点失败不阻塞
- 每次状态流转生成 `docs/reports/` 报告 + 追加 `claude-progress.txt`

### 跨会话持久性
- `features.active.json` + `features.archive.json` 持久化任务状态
- `harness-history.jsonl` 记录所有状态转换历史
- `session-catchup.py` 在会话中断后自动恢复

### 性能考量
- 状态分片 (active/archive) 减少每次加载的 Token 量（约 78%）
- Hook timeout 限制 (PreToolUse/PostToolUse: 10s, PostToolUse format-all: 15s)
- `parallel_group` 支持并行任务执行

---

_架构分析：2026-06-14_
