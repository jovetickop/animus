# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库性质

本仓库是 **Claude Code 技能插件 `harness-cc` 本身的开发仓库**，不是使用该插件的目标工程。仓库根目录没有 `CMakeLists.txt` / `Cargo.toml` / `package.json` 等业务工程文件——所有源代码、脚本、模板、Agent 定义都集中在根目录各子目录中。

`SKILL.md` 是技能入口（被 Claude Code 通过 `/harness-cc` 激活时读取），`templates/init-project.ps1` 是安装入口（用户执行后把插件资产复制到目标工程）。

## 仓库根结构

```
ty-qt-ai-plugin/                       仓库根（插件发布源）
├── SKILL.md                           技能入口（/harness-cc 触发）
├── README.md                          中文使用文档
├── .gitignore                         排除 CLAUDE.md、本地 settings、worktrees、运行时状态
├── agents/                            16 个 Agent 定义（按语言分组）
│   ├── base/                          基础核心（被各语言 agent 引用）
│   ├── universal/                     跨语言通用 Agent（5 个）
│   ├── qt/ / cpp-cmake/               C++ 专项
│   ├── python/ / node/ / rust/ / go/   各语言专项
│   └── frontend/                      前端专项
├── commands/                          3 个斜杠命令 + 验证脚本
├── docs/                              开发文档（编码策略、Hook 调试、模板说明）
├── hooks/                             PostToolUse 自动 clang-format 等运行时钩子
├── rules/                             8 个编码规范文件（按语言分组）
├── scripts/                           Python 脚本（session-catchup、状态显示等）
├── skills/tdd-workflow/               子技能（/tdd-workflow）
└── templates/                         安装时使用的模板
    ├── harness/                       状态机脚本（features.json + 7 个脚本）
    ├── existing_project/              CLAUDE.md / review-checklist / cmake-adapter 模板
    ├── .clang-format                  C++ 格式化配置
    ├── .mcp.json                      MCP 服务器模板
    └── init-project.ps1               项目初始化主脚本
```

## 三层架构

插件按"技能入口 → 编排命令 → 执行 Agent + 规则"组织：

1. **技能入口** (`SKILL.md`)：被 `/harness-cc` 激活后判定项目状态。
2. **编排命令** (`commands/`)：3 个斜杠命令驱动工作流
   - `harness-code-setup`：复制资产 + 检测项目类型（CMake/Qt/Cargo/npm/pip）+ 回填命令
   - `harness-code-plan`：PRD+方案 → `features.json` 任务列表
   - `harness-code-review`：通用 + 语言专项验收
3. **执行层** (`agents/` + `rules/`)：universal 5 个通用 + 各语言专项 Agent；rules 约束编码规范。

## Agent 索引（按职责）

| 目录 | Agent | 职责 |
|------|-------|------|
| `agents/universal/` | `feature-planner` | PRD → features.json |
| | `task-implementer` | 单任务最小闭环实现 |
| | `test-engineer` | 通用测试设计 |
| | `build-doctor` | 构建诊断 |
| | `code-reviewer` | 通用代码审查 |
| `agents/qt/` | `architect` / `task-implementer` / `test-engineer` / `ui-reviewer` | C++/Qt 4 件套 |
| `agents/cpp-cmake/` | `architect` | 纯 C++ 架构（搭配 universal 实现/测试） |
| `agents/python/` | `architect` / `test-engineer` | Python 2 件套 |
| `agents/node/` | `architect` / `test-engineer` / `ui-reviewer` | Web 3 件套（含 a11y/性能审查） |
| `agents/rust/` | `architect` / `test-engineer` | Rust 2 件套 |

> 新增 Agent 时保持 `description: ...` frontmatter 格式——这是 Claude Code 触发 Agent 的关键匹配文本。

## 状态机核心规则（修改时必须遵守）

`templates/harness/` 是状态机的实现，逻辑由 `update-progress.ps1` 强制执行：

- 状态机：`pending → in_progress → passed/failed`；`failed → in_progress` 重试；`pending` 只能从 `failed/in_progress/pending` 改回。
- 同时只能有一个 `in_progress` 任务（脚本会拒绝第二个）。
- `in_progress → passed` 必须有构建/测试证据，否则违反工作流硬规则。
- `depends_on` 必须是直接前置任务 ID；前置任务未 `passed` 时不能进入 `in_progress`。
- 每次状态流转自动追加 `claude-progress.txt` 一行 + 生成 `docs/reports/<TaskId>-<name>.md` 报告。
- `updated_at` / `last_error` 由脚本维护，不要手工批量改写。
- 状态非法流转脚本会 `exit 1` 并打印原因——这是契约，不应放宽。

## hooks 行为

`hooks/hooks.json` 注册了 `PostToolUse` 钩子：每次 Write/Edit 后对 `*.cpp|*.cc|*.cxx|*.c|*.h|*.hpp|*.hxx` 调 `clang-format`。脚本通过 `${CLAUDE_PLUGIN_ROOT}` 解析路径；两条平台分支（bash + PowerShell）互为降级，失败时 `exit 0` 不阻塞。

修改 hooks 时注意：`timeout: 10`（秒），且必须保持"失败不阻塞"语义，否则会拖慢所有 Write/Edit。

## 模板与目标工程约定

- `templates/existing_project/CLAUDE.md` 是**追加式**合并模板（`<!-- harness-cc -->` 哨兵），不是覆盖。修改时不要破坏哨兵标记。
- `templates/init-project.ps1` 复制资产到目标工程；步骤 9 的"检查/追加 CLAUDE.md"是核心合并逻辑。
- `templates/harness/features.json` 里的字段顺序（id/name/status/depends_on/priority/test_command/last_error/updated_at/acceptance_criteria）是契约，新字段必须保证向后兼容。

## 修改本仓库时的常用命令

```bash

# 语法快速检查（PowerShell 脚本）

powershell -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw 'templates/harness/update-progress.ps1'), [ref]$null); 'ok'"

# Python 脚本快速检查（兼容 Py2/3）

python -m py_compile templates/harness/show-status.py

# JSON 校验

python -m json.tool templates/harness/features.json > /dev/null
python -m json.tool templates/harness/project-config.json > /dev/null
```

本仓库没有构建步骤；CI 通常在多语言目标工程上跑（参考 `rules/universal/testing.md`）。

## 开发/提交约定

- 用户全局规则要求 **不在本仓库自动 push 远程**，只本地提交，由用户自行推送。
- 修改 harness 技能后需走"全语言回归"：至少 3 种语言（C++/Qt、Rust、Python）跑 `Setup → Plan → Implement → Review → Verify → commit` 完整链路，最后用 `skill-creator` 评估。
- commit 信息遵循 `rules/universal/git-workflow.md` 的 Conventional Commits 风格。
- 新增 Agent 描述要写明触发场景，否则 Claude Code 不会自动委派。

## 用户私有规则中的关键约束

- 任务实现优先交给 subagent；本仓库内的小改动可直做，但涉及 3 个以上文件或 50 行以上时**必须拆分**给多个 subagent。
- 输出统一中文；代码注释中文。
- 失败/跳过/降级必须显式说明，不允许 silent cap。
- 跨 Git 目录工作时按 `codegraph init -i` / `codegraph sync` 同步索引。

## Project

**ty-qt-ai-plugin (harness-cc)**

`harness-cc` 是一个 Claude Code 技能插件式的编码工作流引擎。采用微内核 + 插件风格架构，核心层提供状态机引擎和运行时钩子，语言专属插件通过 Agent 定义和编码规则扩展支持 6 种语言生态（C++/Qt、C++/CMake、Python、Node.js、Rust、Go）。该仓库是插件本身的开发仓库，而非使用该插件的目标工程。

**Core Value:** 对于使用 Claude Code 进行多语言开发的团队，harness-cc 提供了一套结构化的代码审查和测试编排框架，核心价值是**"让 AI 辅助的编码工作可跟踪、可验证、可重复"**。

### Constraints

- **向后兼容**：`features.json` 的字段顺序和契约不能更改，现有模板和已安装项目依赖这些格式
- **PowerShell 5.1 兼容**：核心脚本必须兼容 Windows 自带的 PowerShell 5.1，不能仅依赖 PowerShell 7+ 特性
- **Python 双兼容**：所有 .py 脚本必须兼容 Python 2.7+ 和 Python 3.x
- **跨平台不阻塞**：Hooks 脚本失败时必须以 `exit 0` 不阻塞工作流，此语义必须保持
- **本地提交**：本仓库不做自动远程推送，所有提交由用户手动推送

## Technology Stack

## 语言分布

| 语言 | 占比 | 用途 |
|------|------|------|
| PowerShell | ~45% | 核心状态机引擎、项目初始化编排、会话管理、回归测试运行器、hook 脚本 |
| Python | ~30% | 状态显示、状态机替代实现、编码桥接（GBK/UTF-8）、多语言格式化分发、会话恢复、验证脚本 |
| Markdown | ~20% | Agent 定义（16 个）、技能入口（SKILL.md）、编码规范规则、命令文档 |
| JSON | ~5% | 配置（hooks.json、settings.local.json、.mcp.json、project-config.json、features.json） |
| Shell (Bash) | ~3% | 跨平台 hook 降级脚本（clang-format、pre-tool-use、pre-compact、stop-check） |
| YAML / TOML | 无 | 不在本仓库中使用 |

## 运行时要求

| 运行时 | 版本要求 | 用途 |
|--------|----------|------|
| PowerShell | 5.1+（Windows） | 主要运行时，所有 .ps1 脚本 |
| Python | 2.7+ / 3.x 双兼容 | 所有 .py 脚本，含 Python 2/3 兼容层（`from __future__`） |
| Bash | 任意 POSIX shell | 跨平台 hook 降级（.sh 脚本） |
| Node.js | 任意（通过 npx） | MCP 服务器运行时（filesystem/git/memory/linear） |
| Git | 任意 | 版本控制、提交工作流 |

## 核心框架/库

### MCP 服务器（通过 npx 动态加载）

| 包 | 用途 | 来源 |
|----|------|------|
| `@modelcontextprotocol/server-filesystem` | 读写 features.json 等状态文件，避免编码问题 | npm（npx 运行） |
| `@modelcontextprotocol/server-git` | Git 操作集成 | npm（npx 运行） |
| `@modelcontextprotocol/server-memory` | 对 harness-history.jsonl 进行语义查询 | npm（npx 运行） |
| `@linear/mcp-server` | Linear 问题跟踪集成 | npm（npx 运行） |

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

- `json`, `os`, `sys`, `subprocess`, `argparse`, `datetime`, `re`, `time`, `glob`, `io`, `argparse`

## 配置文件体系

| 文件 | 用途 |
|------|------|
| `.claude/settings.local.json` | Claude Code 本地权限白名单（此仓库也保留在 `.claude/` 下）（Bash/Read/MCP/skill 调用） |
| `hooks/hooks.json` | 注册 PostToolUse/PreToolUse/PreCompact/Stop 四个钩子 |
| `templates/.mcp.json` | MCP 服务器连接配置模板（filesystem/git/memory/linear） |
| `templates/harness/project-config.json` | 目标项目类型配置（frontend/backend/verify 字段） |
| `templates/.clang-format` | C++ 格式化规则模板 |
| `SKILL.md` | 技能入口（被 `/harness-cc` 命令触发时读取） |
| `.gitignore` | 排除 CLAUDE.md、settings.local.json、worktrees、.codegraph/ |

## 构建系统

- CMake（含 Qt 检测）→ `cpp-qt` / `cpp-cmake`
- Cargo.toml → `rust`
- go.mod → `go`
- package.json → `node`
- pyproject.toml / requirements.txt → `python`
- 无匹配 → `generic`

## Claude Code 钩子系统

| 钩子类型 | 触发时机 | 实现脚本 |
|---------|---------|---------|
| PreToolUse | Write/Edit 前 | `pre-tool-use.sh` / `pre-tool-use.ps1`（备份 features.json + GBK→UTF-8） |
| PostToolUse | Write/Edit 后 | `clang-format.sh` / `clang-format.ps1` + `format-all.py`（多语言格式化 + UTF-8→GBK） |
| PreCompact | 上下文压缩前 | `pre-compact.sh` / `pre-compact.ps1`（刷进度到 claude-progress.txt） |
| Stop | 会话结束时 | `stop-check.sh` / `stop-check.ps1`（检查未完成任务，输出恢复提示） |

## 平台注意事项

- **PowerShell 脚本用 UTF-8 编码**（CLAUDE.md 明确指出使用 UTF-8 无 BOM 编码，已修复 BOM 问题）
- **Python 脚本兼容 Python 2/3**：使用 `from __future__ import print_function, unicode_literals`，`subprocess.Popen` + `communicate()`
- **跨平台降级**：所有 hook 脚本同时提供 `.sh` 和 `.ps1` 两种版本，互为 fallback
- **GBK 编码支持**：通过 `encoding-bridge.py` 实现 GBK ↔ UTF-8 双向转换，仅作用于 C/C++ 源文件

## Conventions

## 语言级规范

| 语言 | 规范文件 | 范围 |
|------|---------|------|
| 通用 (Universal) | `rules/universal/coding-style.md` | 所有项目共用 |
| C++/CMake | `rules/cpp-cmake/best-practices.md` | 纯 C++ 项目 |
| C++/Qt | `rules/qt/best-practices.md` | C++/Qt 项目 |
| Python | `rules/python/best-practices.md` | Python 项目 |
| Node/TypeScript | `rules/node/best-practices.md` | Node/Web 项目 |
| Rust | `rules/rust/best-practices.md` | Rust 项目 |
| Go | `rules/go/best-practices.md` | Go 项目 |
| 前端组件 | `rules/frontend/component-guidelines.md` | React/Vue 组件 |
| Qt UI 架构 | `rules/qt/ui-architecture.md` | Qt 界面布局 |
| GBK 编码 | `rules/cpp-cmake/encoding.md` | Windows 中文编码 |

### C++ 标准选择 (`.claude/rules/cpp-cmake/best-practices.md`)

- 新项目默认 **C++17**，需 concepts/ranges/coroutines 时用 C++20。
- `CMakeLists.txt` 中显式声明 `set(CMAKE_CXX_STANDARD 17)` 和 `set(CMAKE_CXX_STANDARD_REQUIRED ON)`。
- CMake 最低版本要求 `3.21`。
- 启用 `CMAKE_EXPORT_COMPILE_COMMANDS` 方便静态分析。
- 使用 `target_include_directories`、`target_link_libraries` 替代全局设置。
- 使用 `FetchContent` 管理第三方依赖。

### Python 标准 (`.claude/rules/python/best-practices.md`)

- 新项目默认 Python 3；系统工具脚本需兼容 Python 2.7+ 和 3.x。
- 遵循 PEP 8 风格，行宽 88 字符（兼容 `black`）。
- 所有 public 函数必须有类型注解。
- import 顺序：标准库 → 第三方 → 本地模块，每组空一行。
- 禁止 `from module import *`。

### Node/TypeScript 标准 (`.claude/rules/node/best-practices.md`)

- ESLint 使用 `@typescript-eslint` 规则集，Prettier 负责格式化。
- 前端默认 Vite，库工具包优先使用 tsup 或 esbuild。
- 锁定依赖版本，定期运行 `npm audit`。
- CI 中加入 `lint` 步骤。

### Rust 标准 (`.claude/rules/rust/best-practices.md`)

- 所有代码必须通过 `cargo clippy -- -D warnings` 无警告。
- `unsafe` 必须封装在安全抽象内，每个 `unsafe` 块附 `// Safety: ...` 注释。
- 域错误使用 `thiserror`，顶层使用 `anyhow::Result`。
- 使用 `cargo fmt` 统一格式，每行不超过 100 字符。

### Go 标准 (`.claude/rules/go/best-practices.md`)

- 使用 Go 1.21+，代码必须通过 `gofmt` 格式化。
- 使用 `go vet` 静态检查。
- 使用 `error` 返回值而非 panic；库代码禁止 panic。

### GBK 编码支持 (`.claude/rules/cpp-cmake/encoding.md`)

- 在 `.claude/harness/project-config.json` 中设置 `"encoding": "gbk"` 启用。
- PreToolUse 钩子自动 GBK → UTF-8 转换，PostToolUse 自动 UTF-8 → GBK 回转。
- Agent 不需手动编码转换，hooks 自动完成。

## 命名约定

### 通用命名 (`universal/coding-style.md`)

| 类型 | 规则 | 示例 |
|------|------|------|
| 类型/类/接口 | `PascalCase` | `UserManager` |
| 函数/方法 | `camelCase` 或 `snake_case` | `loadProject()` |
| 局部变量 | `snake_case` 或 `camelCase` | `current_index` |
| 常量/枚举 | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| 文件名 | `snake_case` 或 `kebab-case` | `user_manager` |
| 私有成员 | 前导下划线 | `_cache` |

### 语言特殊约定

| 语言 | 约定 | 文件 |
|------|------|------|
| Go 包名 | 全小写，简短无下划线 | `.claude/rules/go/best-practices.md` |
| Go 文件 | snake_case | `user_service.go` |
| Go 测试文件 | `*_test.go` | `user_service_test.go` |
| Python 模块 | 短小全小写 | `data_loader.py` |
| Node 目录 | 小写 kebab-case | `user-profile/` |
| 前端组件文件 | PascalCase | `GoBoard.tsx` |
| 前端 Hook 文件 | `use` 前缀 camelCase | `useGameState.ts` |

### Agent 定义文件命名

- Agent 文件位于 `agents/{lang}/` 目录，使用蛇形命名：`task-implementer.md`、`test-engineer.md`、`code-reviewer.md`。
- 新增 Agent 时需在 frontmatter 包含 `description` 字段——这是 Claude Code 触发 Agent 的关键匹配文本。

## 文件组织约定

### 通用组织原则 (`universal/coding-style.md`)

- 一个文件尽量只定义一个主要 public 类型。
- 目录组织优先按 **功能/领域** 划分，而非按文件类型堆砌。
- 模块/包内文件职责清晰，避免单文件承载多种不相关逻辑。

### 文件结构顺序

- 外部库使用 `<...>`，项目内头文件使用 `"..."`。
- 实现文件第一行通常是对应的头文件。
- 能前置声明的类型优先前置声明。

### 前端组件组织 (`frontend/component-guidelines.md`)

### 仓库根结构（本仓库）

### Python import 顺序 (`python/best-practices.md`)

## 注释规范

### 通用注释原则 (`universal/coding-style.md`)

- 注释优先解释 **"为什么"**，不要重复代码已经表达清楚的"做了什么"。
- 注释默认使用 **中文**，保持简洁、明确。
- 公共接口、复杂状态机、线程边界、资源释放点建议补充注释。
- `TODO` 必须写清楚后续动作，不要只留"待优化"。
- 本项目所有源代码、Agent 定义、规范文件均使用中文注释。

### Rust unsafe 注释 (`rust/best-practices.md`)

### 前端组件注释 (`frontend/component-guidelines.md`)

## 格式要求

### 通用格式 (`universal/coding-style.md`)

- 统一 **4 空格缩进**，禁止使用 Tab。
- 类、函数、`if/for/while/switch` 的左大括号换行。
- 单行 `if/for` 在逻辑非常简单时可省略大括号；多行分支必须加大括号。
- 每行不超过 **100 个字符**（Python 例外：88 字符兼容 `black`）。
- 连续空行不超过 1 行。
- 格式统一交给格式化工具，不要手动对齐。

### 自动格式化

- **C/C++**：`hooks.json` 注册了 PostToolUse 钩子，每次 Write/Edit 后自动运行 `clang-format`（`templates/.clang-format` 配置）。
- **多语言格式化**：`format-all.py` 自动根据文件扩展名分发到 black/prettier/cargo fmt/clang-format。
- 钩子两条平台分支（bash + PowerShell）互为降级，失败时 `exit 0` 不阻塞。
- 超时限制 10-15 秒，由 `hooks.json` 中的 `timeout` 控制。

### 语言特定格式

| 语言 | 格式化工具 | 额外要求 | 文件 |
|------|-----------|---------|------|
| C++ | clang-format | MSVC `/W4`, GCC/Clang `-Wall -Wextra -Wpedantic` | `rules/cpp-cmake/best-practices.md` |
| Go | gofmt / go fmt | `go vet` 静态检查 | `rules/go/best-practices.md` |
| Rust | cargo fmt | `cargo clippy -- -D warnings` | `rules/rust/best-practices.md` |
| Node | Prettier | ESLint `@typescript-eslint` | `rules/node/best-practices.md` |
| Python | black | 88 字符行宽 | `rules/python/best-practices.md` |

## Git 工作流规范

### Commit 消息格式 (`.claude/rules/universal/git-workflow.md`)

- <变更点 1>
- <变更点 2>
- `task id` 可选，例如 `T013 `（注意后面有空格）。
- 标题一句话说清"做了什么"。
- 正文用要点列出关键改动与影响。

### 分支与变更约束

- 每次改动保持聚焦，便于 review。
- 开 PR 前先检查完整分支差异。
- 当工作流、模板或命令变化时，同步更新文档。
- 每个任务在验收通过后都要提交并推送。

### 本仓库特殊约定 (CLAUDE.md)

- **不在本仓库自动 push 远程**，只本地提交，由用户自行推送。
- 修改 harness 技能后需走 **全语言回归**：至少 3 种语言（C++/Qt、Rust、Python）跑完整工作流。
- 用户全局规则：跨 Git 目录时执行 `codegraph sync`。

### 提交前检查

- 构建通过。
- 相关测试通过。
- 已清理调试代码和临时日志。
- Commit 信息与实际改动一致。

## 代码审查标准

### 审查流程 (SKILL.md / `agents/universal/code-reviewer.md`)

### 严重级别输出

- **critical/high**：必须修复后才能继续。
- **medium/low**：记录待办后可继续。

### 验收审查 (`harness-code-review` 命令)

- `.claude\commands\validate-features.ps1` — 验证 `features.json` 结构。
- `.claude\commands\check-consistency.ps1` — 检查 `features.json` 与 `claude-progress.txt` 状态一致性。

### 状态机验收硬规则 (CLAUDE.md)

- `in_progress → passed` 必须有构建/测试证据。
- 不得标记任务为 `passed` 之前跳过验证。
- 必须执行 `verify_command` 并确认 `exit 0`。
- 验证输出写入 `claude-progress.txt`（至少最后 3 行）。
- 不得修改 `verify_config` 中的 `verify_command`。

### 已有工程验收清单 (`templates/existing_project/review-checklist.md`)

- [ ] 改动是否通过构建/编译？
- [ ] 相关测试是否执行并通过？
- [ ] 代码是否符合项目编码规范？
- [ ] 是否有未处理的错误路径？
- [ ] 是否有调试代码或临时日志残留？
- [ ] harness 状态是否已更新？

### 核心设计约束 (`universal/coding-style.md`)

- 访问修饰符必须显式写出。
- 函数名必须体现动作或结果，避免 `DoWork`、`ProcessData` 空泛命名。
- 参数数量控制在 4 个以内，过多时封装参数对象。
- 嵌套超过 4 层时优先提前返回、拆函数或抽策略。
- 禁止魔法数字，改用常量、枚举或具名配置。
- 优先使用 RAII 和智能指针管理资源。
- 裸指针只用于"不拥有对象"的场景。
- 避免带副作用的全局变量和静态初始化对象。

## Architecture

## 总体架构概览

```text

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
| `/harness-code-setup` | 项目初始化 + 类型检测 + 资产复制 + CLAUDE.md 合并 | `commands/harness-code-setup.md` |
| `/harness-code-plan` | PRD/方案文档 -> features.json 任务列表 | `commands/harness-code-plan.md` |
| `/harness-code-review` | 通用验收 + 语言专项验收 | `commands/harness-code-review.md` |
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
| PreCompact | 上下文压缩前 | 刷写进度到 claude-progress.txt |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 |

### 6. 运行时引擎 (Harness)

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

```

### 状态机流转

```

```

### 初始化数据流

```

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

## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| tdd-workflow | 面向通用 C++/Qt 开发的 TDD 工作流指南，使用 /tdd-workflow 显式调用 | `skills/tdd-workflow/SKILL.md` |
