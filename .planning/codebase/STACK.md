# 技术栈分析

**分析日期:** 2026-06-14

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

本仓库是一个 Claude Code 技能插件开发仓库，不依赖前端/后端框架。其依赖是**工具链级别**的：

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

所有 Python 脚本仅使用**标准库 模块**，无第三方包依赖：
- `json`, `os`, `sys`, `subprocess`, `argparse`, `datetime`, `re`, `time`, `glob`, `io`, `argparse`

## 配置文件体系

| 文件 | 用途 |
|------|------|
| `.claude/settings.local.json` | Claude Code 本地权限白名单（Bash/Read/MCP/skill 调用） |
| `.claude/hooks/hooks.json` | 注册 PostToolUse/PreToolUse/PreCompact/Stop 四个钩子 |
| `.claude/templates/.mcp.json` | MCP 服务器连接配置模板（filesystem/git/memory/linear） |
| `.claude/templates/harness/project-config.json` | 目标项目类型配置（frontend/backend/verify 字段） |
| `.claude/templates/.clang-format` | C++ 格式化规则模板 |
| `SKILL.md` | 技能入口（被 `/harness-cc` 命令触发时读取） |
| `.gitignore` | 排除 CLAUDE.md、settings.local.json、worktrees、.codegraph/ |

## 构建系统

本仓库**无构建步骤**。它是一个 Claude Code 插件仓库，源代码直接运行时读取。

检测脚本（`harness-code-setup.ps1`）支持检测目标项目的构建系统：
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

---

*技术栈分析: 2026-06-14*
