# 目录结构分析
_生成日期：2026-06-14_

## 顶层目录结构

```
ty-qt-ai-plugin/                        ← 仓库根（Claude Code 技能插件 harness-cc 的发布源）
├── SKILL.md                            ← 技能入口文件，/harness-cc 命令激活时被读取
├── README.md                           ← 完整中文使用文档（534 行，含架构图、工作流、目录详细说明）
├── CLAUDE.md                           ← 本仓库的 CLAUDE.md（不是模板，是开发者指引）
├── .gitignore                          ← 排除 CLAUDE.md、本地 settings、worktrees
├── .planning/
│   └── codebase/
│       ├── ARCHITECTURE.md             ← 架构分析文档
│       └── STRUCTURE.md                ← 本文件
├── .claude/                            ← 核心插件资产目录（安装时被 init-project.ps1 复制到目标工程）
│   ├── agents/                         ← 23 个 Agent 定义文件（按语言分组）
│   │   ├── base/                       ←   基础核心文件（HTML 注释引用，不单独使用）
│   │   ├── universal/                  ←   跨语言通用 Agent（5 个）
│   │   ├── cpp-cmake/                  ←   C++/CMake 专属 Agent（1 个）
│   │   ├── qt/                         ←   C++/Qt 专属 Agent（4 个）
│   │   ├── python/                     ←   Python 专属 Agent（2 个）
│   │   ├── node/                       ←   Node.js/Web 专属 Agent（3 个）
│   │   ├── rust/                       ←   Rust 专属 Agent（2 个）
│   │   ├── go/                         ←   Go 专属 Agent（2 个）
│   │   ├── frontend/                   ←   前端补充 Agent（1 个）
│   │   └── README.md                   ←   Agent 索引表
│   ├── commands/                       ← 斜杠命令定义（3 个 .md 命令 + 3 个 .ps1 辅助脚本）
│   │   ├── harness-code-setup.md       ←   初始化命令定义
│   │   ├── harness-code-setup.ps1      ←   初始化 PowerShell 脚本（备选入口）
│   │   ├── harness-code-plan.md        ←   任务拆解命令定义
│   │   ├── harness-code-review.md      ←   验收审查命令定义
│   │   ├── validate-features.ps1       ←   features.json 结构校验脚本
│   │   └── check-consistency.ps1       ←   状态一致性检查脚本
│   ├── rules/                          ← 编码规范（12 个 .md 文件）
│   │   ├── universal/                  ←   通用规范（3 个：编码风格/测试/Git 工作流）
│   │   ├── cpp-cmake/                  ←   C++/CMake 规范（best-practices + encoding 说明）
│   │   ├── qt/                         ←   Qt 规范（best-practices + UI 架构）
│   │   ├── python/                     ←   Python 规范（best-practices）
│   │   ├── node/                       ←   Node.js 规范（best-practices）
│   │   ├── rust/                       ←   Rust 规范（best-practices）
│   │   ├── go/                         ←   Go 规范（best-practices）
│   │   └── frontend/                   ←   前端规范（component-guidelines）
│   ├── hooks/                          ← 自动化钩子系统
│   │   ├── hooks.json                  ←   钩子注册配置（4 种钩子类型）
│   │   └── scripts/                    ←   钩子执行脚本（双平台：.ps1 + .sh）
│   │       ├── pre-tool-use.ps1/.sh    ←   PreToolUse：备份 + GBK→UTF-8
│   │       ├── pre-compact.ps1/.sh     ←   PreCompact：进度刷写
│   │       ├── stop-check.ps1/.sh      ←   Stop：完整性检查
│   │       ├── clang-format.ps1/.sh    ←   C/C++ 代码格式化
│   │       ├── format-all.py           ←   多语言格式化分发（black/prettier/cargo fmt/clang-format）
│   │       └── encoding-bridge.py      ←   GBK/UTF-8 编码桥接
│   ├── scripts/                        ← 技能自带 Python 工具脚本
│   │   └── session-catchup.py          ←   会话恢复工具（/clear 后重建上下文）
│   ├── skills/                         ← 子技能
│   │   └── tdd-workflow/               ←   TDD 工作流技能
│   │       └── SKILL.md                ←   子技能入口文件
│   └── templates/                      ← 安装时使用的模板文件
│       ├── init-project.ps1            ←   主安装脚本（415 行，10 个步骤）
│       ├── .clang-format               ←   C++ 格式化配置模板
│       ├── .mcp.json                   ←   MCP 服务器配置模板（filesystem + git + memory + linear）
│       ├── harness/                    ←   复制到目标项目 .claude/harness/ 的运行时引擎
│       │   ├── features.json           ←   任务清单模板
│       │   ├── project-config.json     ←   项目配置模板
│       │   ├── README.md               ←   运行时说明
│       │   ├── show-status.py          ←   状态概览显示
│       │   ├── update-progress.ps1     ←   核心状态机引擎
│       │   ├── run-regression.ps1      ←   一键构建+测试
│       │   ├── init.ps1                ←   首次初始化引导
│       │   └── coding-session.ps1      ←   会话入口
│       ├── state/                      ←   复制到目标项目 .claude/state/ 的状态文件
│       │   ├── features.json           ←   兼容旧版的任务清单
│       │   ├── features.active.json    ←   活动任务（Token 优化分片）
│       │   ├── features.archive.json   ←   已归档任务
│       │   └── claude-progress.txt     ←   进度日志模板
│       └── existing_project/           ←   回填到目标项目根目录的模板
│           ├── CLAUDE.md               ←   追加式合并的 CLAUDE.md 模板（哨兵标记）
│           ├── review-checklist.md     ←   验收清单模板
│           └── cmake-adapter.md        ←   CMake 接入原则
└── scripts/                            ← 仓库自带的 Python 工具脚本（独立于模板）
    ├── update-progress.py              ← 状态机引擎（PS 脚本的 Python 移植版）
    ├── run-regression.py               ← 一键构建+测试（PS 脚本的 Python 移植版）
    ├── validate-features.py            ← 结构校验 + 循环依赖检测（Kahn 算法）
    └── show-status.py                  ← 状态显示（增强版）
```

## 关键目录职责说明

### `SKILL.md` — 技能入口
- 仓库顶层，不放在 `.claude/` 内
- 被 Claude Code 通过 `/harness-cc` 命令激活时读取
- 包含完整的 Hooks 配置、工作流步骤、状态规则、Agent 选择表
- 既是文档又是执行入口

### `.claude/agents/` — Agent 定义目录
- 所有 Agent 为纯 Markdown 文件（`.md`），不含代码
- 每个 Agent 有 `description` frontmatter 用于 Claude Code 触发匹配
- 分层结构：`base/`（核心引用）→ `universal/`（通用）→ `{lang}/`（语言专属）
- 命名规律：`architect.md` / `task-implementer.md` / `test-engineer.md` / `code-reviewer.md` / `build-doctor.md` / `feature-planner.md` / `ui-reviewer.md`

### `.claude/rules/` — 编码规范目录
- Markdown 文件，按语言分组
- `universal/` 下的规则在所有项目类型中生效
- `{lang}/` 下的规则只在对应项目类型中生效
- 命名规律：`best-practices.md` / `testing.md` / `coding-style.md` / `git-workflow.md` / `component-guidelines.md` / `ui-architecture.md` / `encoding.md`

### `.claude/templates/` — 安装模板目录
- 安装源：`init-project.ps1` 从 `templates/` 读取文件并复制到目标项目
- `templates/harness/` 中的 8 个文件复制目标为 `.claude/harness/`
- `templates/state/` 中的 4 个文件复制目标为 `.claude/state/`
- `templates/existing_project/` 中的 3 个文件复制目标为项目根目录
- `templates/.mcp.json` 和 `templates/.clang-format` 复制目标为项目根目录

### `.claude/hooks/` — 自动化钩子目录
- `hooks.json` 是注册入口，按钩子类型 (PreToolUse/PostToolUse/PreCompact/Stop) 分组
- 每个钩子的 `command` 字段优先调用 `.sh` 版本，失败时降级到 `.ps1` 版本
- 所有钩子以 `exit 0` 结尾保证不阻塞
- `scripts/` 下有 6 个 `.ps1` + 4 个 `.sh` + 2 个 `.py` = 12 个脚本文件

### `.claude/commands/` — 斜杠命令目录
- `.md` 文件是命令定义（被 Claude Code 读取），`.ps1` 文件是辅助执行脚本
- 3 个主要命令: `harness-code-setup`, `harness-code-plan`, `harness-code-review`
- 3 个辅助脚本: `validate-features.ps1`, `check-consistency.ps1`, `harness-code-setup.ps1`

## 文件组织模式

### 按功能领域划分，而非按文件类型
每个功能子系统的文件都在同一目录下：
- Agent 目录：`agents/{group}/` 包含该组所有 Agent 定义
- 规则目录：`rules/{group}/` 包含该组所有规则
- 模板目录：`templates/{subsystem}/` 包含该子系统的所有模板文件

### 单文件单职责
- 每个 Agent 定义文件只定义一个 Agent 角色
- 每个规范文件只关注一个维度（编码风格/测试/Git）
- 每个命令文件只定义一个斜杠命令

### 入口 + 实现分离
- 命令入口：`.md` 文件（Claude Code 读取使用）
- 命令实现：`.ps1` 文件（脚本执行）或 Agent 委派
- 技能入口：`SKILL.md`（顶层）
- 子技能入口：`skills/tdd-workflow/SKILL.md`（嵌套）

### 双平台共存
- PowerShell (`.ps1`) — Windows 优先
- Shell (`.sh`) — Linux/macOS 降级
- Python (`.py`) — 跨平台核心逻辑

## 命名约定

| 类别 | 命名规则 | 示例 |
|------|----------|------|
| Agent 定义文件 | kebab-case + 角色名 | `feature-planner.md`, `task-implementer.md` |
| 规则文件 | kebab-case + 领域名 | `coding-style.md`, `best-practices.md` |
| 命令文件 | kebab-case (harness-code- 前缀) | `harness-code-plan.md` |
| 脚本文件 | kebab-case + 扩展名 | `update-progress.ps1`, `pre-tool-use.sh` |
| 状态文件 | snake_case + 语义名 | `features.active.json`, `claude-progress.txt` |
| 配置文件 | kebab-case | `project-config.json`, `hooks.json` |
| Python 脚本 | snake_case | `session-catchup.py`, `encoding-bridge.py` |
| 模板目录 | snake_case | `existing_project/` |
| 技能目录 | kebab-case | `tdd-workflow/` |
| 语言分组 | kebab-case | `cpp-cmake/` |

### 文件扩展名约定

| 扩展名 | 用途 |
|--------|------|
| `.md` | Agent 定义、命令定义、规则、文档 (Markdown) |
| `.ps1` | PowerShell 脚本 |
| `.sh` | Shell 脚本 |
| `.py` | Python 脚本 |
| `.json` | 配置/状态文件 |
| `.txt` | 纯文本进度日志 |

## 何处放置新代码

### 新增语言支持
1. 创建 `agents/{lang}/` 目录 + 对应 Agent `.md` 文件
2. 创建 `rules/{lang}/` 目录 + 对应规则 `.md` 文件
3. 在 `init-project.ps1` 的 `$TypeMapping` 中添加映射
4. 更新 `SKILL.md` 和 `agents/README.md` 中的 Agent 选择表

### 新增 Agent
1. 在对应语言分组目录下创建 `.md` 文件
2. 确保包含 `description` frontmatter
3. 如果包含通用逻辑，提取到 `agents/base/` 并通过 HTML 注释引用

### 新增 Hook
1. 在 `hooks/scripts/` 下创建 `.ps1` + `.sh` 双平台脚本
2. 在 `hooks/hooks.json` 中注册

### 新增 Command
1. 在 `commands/` 下创建 `.md` 文件 (命令定义)
2. 如需脚本辅助，创建对应的 `.ps1` 文件
3. 在 `SKILL.md` 和 `README.md` 中添加说明

### 新增 Rule
1. 在 `rules/{group}/` 下创建 `.md` 文件
2. 如果跨语言通用，放在 `rules/universal/`
3. 如果语言专属，放在 `rules/{lang}/`

### 新增 Template
1. 根据目标位置选择子目录：
   - 运行时引擎文件 → `templates/harness/`
   - 项目根目录文件 → `templates/existing_project/`
   - 状态文件 → `templates/state/`
2. 在 `init-project.ps1` 中添加复制逻辑

---

_结构分析：2026-06-14_
