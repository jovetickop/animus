# CLAUDE.md

## Project

**animus** — Claude Code 编码工作流引擎。微内核 + 插件架构，状态机引擎和运行时钩子构成核心层，语言插件通过 Agent 和 Rule 扩展 6 种语言。

**Core Value:** "让 AI 辅助的编码工作可跟踪、可验证、可重复"

### Constraints

- **向后兼容**：`features.json` 字段顺序不可变。
- **PowerShell 5.1 兼容**：核心脚本不依赖 PS7+ 特性。
- **Python 双兼容**：所有 `.py` 兼容 2.7+ 和 3.x。
- **跨平台不阻塞**：Hooks 失败时 `exit 0`。
- **本地提交**：不做自动远程推送。
- **子任务优先**：3 个以上文件或 50 行以上改动**必须拆分**给 subagent。
- **输出中文**：文本和代码注释统一中文。
- **显式契约**：失败/跳过/降级必须说明，不允许 silent cap。

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

本仓库是 **animus 插件的源码发布仓库**，不是使用该插件的目标工程。通过 `/plugin marketplace add` + `/plugin install` 或手动克隆后 `/plugin install <path>` 安装，插件目录由 `${CLAUDE_PLUGIN_ROOT}` 解析。仓库根包含所有源代码（agents/, commands/, rules/, hooks/, templates/, scripts/, skills/, docs/），无 `CMakeLists.txt` / `Cargo.toml` / `package.json`。

`.claude-plugin/plugin.json` 是入口，7 个斜杠命令为主要工作流入口。

## 仓库根结构

```
animus/
├── .claude-plugin/plugin.json      插件清单
├── agents/                         22 个 Agent（按语言分组，详见 docs/agent-index.md）
├── commands/                       7 个斜杠命令 + 验证脚本
├── docs/                           参考文档（架构、Agent 索引等）
├── hooks/                          运行时钩子
├── rules/                          13 个编码规范文件
├── scripts/                        Python 工具脚本
├── skills/tdd-workflow/            子技能
└── templates/                      安装模板
    ├── animus/                     状态机脚本 + 状态文件（10+ 文件）
    ├── existing_project/           已有工程模板
    ├── .clang-format               C++ 格式化配置
    └── init-project.ps1            项目初始化入口
```

## 三层架构

```
插件清单 → 编排命令 → 执行层（Agent + Rule）
```

1. **插件清单** (`.claude-plugin/plugin.json`)：声明元信息、命令入口和自动发现组件。
2. **编排命令** (`commands/`)：7 个斜杠命令驱动工作流
   - `animus-init`：检测项目类型 + 创建 `.claude/animus/` 运行时目录
   - `animus-plan`：PRD + 方案 → `features.json` 任务列表
   - `animus-debug`：系统化调试（根因→分析→修复→审查）
   - `animus-review`：通用 + 语言专项验收
   - `animus-handoff`：保存 session 上下文快照
   - `animus-continue`：从 handoff.json 恢复
   - `animus-archive`：归档当前迭代，开始新迭代
3. **执行层** (`agents/` + `rules/`)：通过 `${CLAUDE_PLUGIN_ROOT}` 从插件目录加载。

## 状态机核心规则

状态由 `scripts/engine/cmd_transition.py` 强制执行：

- 状态流：`pending → in_progress → passed/failed`；`failed → in_progress` 重试；`pending` 只能从 `failed/in_progress/pending` 改回。
- 同时只能有一个 `in_progress` 任务。
- `in_progress → passed` 必须有构建/测试证据。
- `depends_on` 必须是直接前置任务 ID；前置未 `passed` 时不能进入 `in_progress`。
- 每次状态流转追加 JSONL 日志 + 生成报告。
- `updated_at` / `last_error` 由脚本维护，不应手工改写。
- 非法流转 `exit 1`——此契约不应放宽。

## 运行时钩子

`hooks/hooks.json` 注册 4 种钩子：

| 钩子 | 触发时机 | 作用 |
|------|---------|------|
| PreToolUse | Write/Edit 前 | 备份 features.json；GBK→UTF-8 转码 |
| PostToolUse | Write/Edit 后 | clang-format + format-all 多语言格式化；UTF-8→GBK 回转 |
| PreCompact | 上下文压缩前 | JSONL compact 事件 + task_plan.md 自动同步 |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 |

每条钩子两条平台分支（bash + PowerShell）互为降级，失败 `exit 0` 不阻塞。修改时注意 `timeout: 10`。

## 模板与目标工程约定

- `init-project.ps1` 为目标项目创建 `.claude/animus/` 运行时目录，不修改目标项目 CLAUDE.md。
- `features.json` 字段顺序（id/name/status/depends_on/priority/test_command/last_error/updated_at/acceptance_criteria）是契约，新字段必须向后兼容。

## 开发/提交约定

- **不在本仓库自动 push 远程**，只本地提交，由用户自行推送。
- 修改 animus 后需走**全语言回归**：至少 C++/Qt、Rust、Python 三种语言跑完整链路，最后 `plugin-validator` 验证。
- commit 信息遵循 Conventional Commits 风格。
- 新增 Agent 描述要写明触发场景，否则 Claude Code 不会自动委派。

## 本仓库常用命令

```bash
# Python 语法检查
python -m py_compile templates/animus/show-status.py
# JSON 校验
python -m json.tool templates/animus/features.json > /dev/null
python -m json.tool templates/animus/project-config.json > /dev/null
```

本仓库无构建步骤；CI 在多语言目标工程上跑。

## 参考文档

| 内容 | 位置 |
|------|------|
| Agent 索引（22 个 Agent 职责） | `docs/agent-index.md` |
| 架构分层、设计模式、运行时要求 | `docs/architecture.md` |
| 编码规范（通用 + 所有语言） | `rules/` |
| Git 工作流 | `rules/universal/git-workflow.md` |
| 代码审查标准 | `commands/animus-review.md` |
| 状态机验收硬规则 | `commands/animus-review.md` |
| Project Skills | `skills/tdd-workflow/SKILL.md` |




