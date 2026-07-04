# CLAUDE.md

## 规则

### Gap Analysis
规划前输出"已实现 vs 原定计划"差距清单，标注缺失项和影响，经确认后才实施。

### Sync Docs
每次功能变更后同步更新 README.md、CLAUDE.md 和相关模板、规则文件、Agent 定义中的文档引用。

### Use RTK
文件读取用 `rtk read --level minimal`，内容搜索用 `rtk grep`，目录列表用 `rtk ls`，差异用 `rtk git diff`。仅需完整精确内容时用内置 Read/Grep/Glob。

### 执行后审查
每个命令执行完后用 code-reviewer agent 审查：改了哪些文件、是否改对、遗漏或错误。通过后才继续。

## 仓库性质

本仓库是 **animus 插件的源码发布仓库**，不是使用该插件的目标工程。通过 `/plugin marketplace add` + `/plugin install` 或手动克隆后 `/plugin install <path>` 安装，插件目录通过 `${CLAUDE_PLUGIN_ROOT}` 解析。仓库根包含所有源代码（agents/, commands/, rules/, hooks/, templates/, scripts/, skills/, docs/），无 `CMakeLists.txt` / `Cargo.toml` / `package.json`。

`.claude-plugin/plugin.json` 是入口，7 个斜杠命令为主要工作流入口。`templates/init-project.ps1` 是手动安装入口。

## 仓库根结构

```
animus/                             仓库根（插件发布源）
├── .claude-plugin/plugin.json          插件清单
├── README.md                          中文使用文档
├── .gitignore                         排除 CLAUDE.md、settings、worktrees、运行时状态
├── agents/                            22 个 Agent 定义（按语言分组，详见 docs/agent-index.md）
├── commands/                          7 个斜杠命令 + 验证脚本
├── docs/                              开发文档（架构、Agent 索引等参考内容）
├── hooks/                             PostToolUse 自动 clang-format 等运行时钩子
├── rules/                            13 个编码规范文件（按语言分组）
├── scripts/                           Python 脚本（session-catchup、format-log、状态显示等）
├── skills/tdd-workflow/               子技能（/tdd-workflow）
└── templates/                         安装时使用的模板
    ├── animus/                       状态机脚本 + 状态文件（task_plan.md、findings.md 等 10+ 文件）
    ├── existing_project/              CLAUDE.md / review-checklist / cmake-adapter 模板
    ├── .clang-format                  C++ 格式化配置
    └── init-project.ps1               项目初始化主脚本
```

## 三层架构

插件按"插件清单 → 编排命令 → 执行 Agent + 规则"组织：

1. **插件清单** (`.claude-plugin/plugin.json`)：声明元信息、命令入口和自动发现组件。
2. **编排命令** (`commands/`)：7 个斜杠命令驱动工作流
   - `animus-setup`：检测项目类型 + 创建 `.claude/animus/` 运行时目录
   - `animus-plan`：PRD+方案 → `features.json` 任务列表
   - `animus-debug`：系统化调试——根因调查→模式分析→假设验证→修复规划→自动审查
   - `animus-review`：通用 + 语言专项验收
   - `animus-handoff`：保存 session 上下文快照到 handoff.json
   - `animus-continue`：从 handoff.json 恢复 session 上下文
   - `animus-archive`：归档当前迭代，清空并开始新迭代
3. **执行层** (`agents/` + `rules/`)：从插件安装目录通过 `${CLAUDE_PLUGIN_ROOT}` 加载。完整 Agent 列表见 `docs/agent-index.md`，规则见 `rules/`。

## 状态机核心规则

`templates/animus/` 是状态机实现，`update-progress.ps1` 强制执行：

- 状态流：`pending → in_progress → passed/failed`；`failed → in_progress` 重试；`pending` 只能从 `failed/in_progress/pending` 改回。
- 同时只能有一个 `in_progress` 任务。
- `in_progress → passed` 必须有构建/测试证据。
- `depends_on` 必须是直接前置任务 ID；前置未 `passed` 时不能 `in_progress`。
- 每次状态流转追加 `.claude/animus/animus-history.jsonl` + 生成 `.claude/animus/docs/<TaskId>-<name>.md` 报告。
- `updated_at` / `last_error` 由脚本维护。
- 非法流转脚本 `exit 1`——此契约不应放宽。

## hooks 行为

`hooks/hooks.json` 注册 `PostToolUse`：每次 Write/Edit 后对 `*.cpp|*.cc|*.cxx|*.c|*.h|*.hpp|*.hxx` 调 `clang-format`。两条平台分支（bash + PowerShell）互为降级，失败 `exit 0` 不阻塞。

修改 hooks 注意：`timeout: 10`，保持"失败不阻塞"语义。

## 模板与目标工程约定

- `init-project.ps1` 为目标项目创建 `.claude/animus/` 运行时目录，不修改目标项目 CLAUDE.md。
- `features.json` 字段顺序（id/name/status/depends_on/priority/test_command/last_error/updated_at/acceptance_criteria）是契约，新字段必须向后兼容。

## 修改本仓库常用命令

```bash
# PowerShell 语法检查
powershell -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw 'templates/animus/update-progress.ps1'), [ref]$null); 'ok'"
# Python 语法检查
python -m py_compile templates/animus/show-status.py
# JSON 校验
python -m json.tool templates/animus/features.json > /dev/null
python -m json.tool templates/animus/project-config.json > /dev/null
```

本仓库无构建步骤；CI 在多语言目标工程上跑。

## 开发/提交约定

- **不在本仓库自动 push 远程**，只本地提交，由用户自行推送。
- 修改 animus 后需走**全语言回归**：至少 3 种语言（C++/Qt、Rust、Python）跑完整链路，最后 `plugin-validator` 验证。
- commit 信息遵循 Conventional Commits 风格。
- 新增 Agent 描述要写明触发场景，否则 Claude Code 不会自动委派。

## 用户私有规则关键约束

- 任务实现优先 subagent；3 个以上文件或 50 行以上改动**必须拆分**。
- 输出中文；代码注释中文。
- 失败/跳过/降级显式说明，不允许 silent cap。
- 跨 Git 目录时 `codegraph init -i` / `codegraph sync`。

## Project

**animus** — Claude Code 编码工作流引擎。微内核 + 插件架构，核心层提供状态机引擎和运行时钩子，语言插件通过 Agent 和 Rule 扩展支持 6 种语言。

**Core Value:** "让 AI 辅助的编码工作可跟踪、可验证、可重复"。

### Constraints

- **向后兼容**：features.json 字段顺序不能改。
- **PowerShell 5.1 兼容**：核心脚本不能仅依赖 PS7+。
- **Python 双兼容**：所有 .py 兼容 2.7+ 和 3.x。
- **跨平台不阻塞**：Hooks 失败 `exit 0`。
- **本地提交**：不做自动远程推送。

## 参考文档

| 内容 | 位置 |
|------|------|
| Agent 索引（22 个 Agent 职责） | `docs/agent-index.md` |
| 架构分层、设计模式、决策记录、运行时要求 | `docs/architecture.md` |
| 编码规范（通用 + 所有语言） | `rules/` 目录，按语言分组 |
| Git 工作流 | `rules/universal/git-workflow.md` |
| 代码审查标准 | `commands/animus-review.md` / `agents/universal/code-reviewer.md` |
| 状态机验收硬规则 | `commands/animus-review.md` |
| Project Skills | `skills/tdd-workflow/SKILL.md` |
