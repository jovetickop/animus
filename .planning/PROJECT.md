# ty-qt-ai-plugin (harness-cc)

## What This Is

`harness-cc` 是一个 Claude Code 技能插件式的编码工作流引擎。采用微内核 + 插件风格架构，核心层提供状态机引擎和运行时钩子，语言专属插件通过 Agent 定义和编码规则扩展支持 6 种语言生态（C++/Qt、C++/CMake、Python、Node.js、Rust、Go）。该仓库是插件本身的开发仓库，而非使用该插件的目标工程。

## Core Value

对于使用 Claude Code 进行多语言开发的团队，harness-cc 提供了一套结构化的代码审查和测试编排框架，核心价值是**"让 AI 辅助的编码工作可跟踪、可验证、可重复"**。

## Requirements

### Validated

现有代码库已验证的能力（来自已完成的功能实现）：

- ✓ **技能入口系统** — 通过 `/harness-cc` 命令激活技能，判定项目状态后路由到对应命令
- ✓ **三层架构** — 技能入口层→编排层（3 个斜杠命令）→执行层（23 个 Agent + 12 个规则文件）
- ✓ **多语言 Agent 支持** — 覆盖 universal、C++/Qt、C++/CMake、Python、Node.js、Rust、Go
- ✓ **状态机引擎** — `pending → in_progress → passed/failed` 状态流转，含 Oracle 验证
- ✓ **项目初始化** — `init-project.ps1` 自动检测项目类型、复制资产、生成配置
- ✓ **跨平台 Hooks** — PreToolUse / PostToolUse / PreCompact / Stop 四个钩子，bash+Powershell 双降级
- ✓ **多语言格式化** — Python (black/autopep8)、JS/TS (prettier/eslint)、Rust (cargo fmt)、C++ (clang-format)
- ✓ **GBK 编码支持** — 编码桥接自动处理 GBK ↔ UTF-8 转换
- ✓ **进度跟踪** — `claude-progress.txt` + Markdown 报告 + Git 自动提交
- ✓ **MCP 服务器集成** — filesystem、git、memory、Linear

### Active

- [ ] **TECHD-01**: 统一脚本编码为 UTF-8 with BOM（7 个 UTF-16LE .ps1 文件 → UTF-8）
- [ ] **TECHD-02**: 修复 Shell 脚本换行符（.sh 文件 CRLF → LF）
- [ ] **TECHD-03**: 修复 UTF-16LE 脚本内已损坏的中文注释
- [ ] **TECHD-04**: 统一 `features.json` 标准路径为 `.claude/state/`，消除双重查找逻辑
- [ ] **TECHD-05**: 清理 `templates/state/` 目录文件，明确三个 JSON 模板的角色
- [ ] **TECHD-06**: 拆分 `update-progress.ps1`（424 行 → 模块化）
- [ ] **TECHD-07**: 替换 `Invoke-Expression` 为安全的命令执行方式
- [ ] **TECHD-08**: 修复 Hooks 脚本中正则解析 JSON 为 `ConvertFrom-Json`
- [ ] **TECHD-09**: 修复 `format-all.py` Rust 双重 `cargo fmt` 及缓存 `Cargo.toml` 查找
- [ ] **TECHD-10**: 修复 `init-project.ps1` 硬编码用户技能路径问题
- [ ] **TECHD-11**: 补充编码策略、模板角色、钩子调试方式等缺失文档

### Out of Scope

- 重构整个状态机引擎为不同语言（保持现有 PowerShell 实现）
- 新增语言支持（如 Swift/Kotlin/Java）
- 新增功能特性（非技术债务范畴的新能力）
- 修改 `features.json` 字段契约（保持向后兼容）

## Context

本仓库是 `harness-cc` 技能的开发仓库，是一个较为成熟的技能插件。代码库映射分析显示以下背景信息：

- **技术栈**：PowerShell (~45%)、Python (~30%)、Markdown (~20%)，无第三方 Python 依赖（仅用标准库）
- **运行时要求**：PowerShell 5.1+、Python 2.7+/3.x 双兼容、Bash（任意 POSIX）
- **已知问题**：7 个技术债务项已系统化梳理，包括编码碎片、路径管理重复、脚本臃肿、安全风险等
- **开发流程**：修改后需在 3 种及以上语言的目标工程中跑完整 Setup→Plan→Implement→Review→Verify 回归链路

## Constraints

- **向后兼容**：`features.json` 的字段顺序和契约不能更改，现有模板和已安装项目依赖这些格式
- **PowerShell 5.1 兼容**：核心脚本必须兼容 Windows 自带的 PowerShell 5.1，不能仅依赖 PowerShell 7+ 特性
- **Python 双兼容**：所有 .py 脚本必须兼容 Python 2.7+ 和 Python 3.x
- **跨平台不阻塞**：Hooks 脚本失败时必须以 `exit 0` 不阻塞工作流，此语义必须保持
- **本地提交**：本仓库不做自动远程推送，所有提交由用户手动推送

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 统一编码方向为 UTF-8 with BOM | PowerShell 5.1 和 7.x 均支持 UTF-8 with BOM，且 Git diff 可读性好 | — Pending |
| 标准状态路径为 `.claude/state/features.json` | 旧路径 `.claude/harness/` 与状态机脚本目录混淆，分离后职责清晰 | — Pending |
| 分阶段推进修复 | 部分修复有依赖关系（编码统一前置），拆分后每阶段可独立验证 | — Pending |
| 同步补充文档 | 避免同样问题再次发生，降低新维护者的入门成本 | — Pending |
| 全语言回归验证 | 确保编码/换行符/路径等基础设施修改不破坏各语言工作流 | — Pending |

---

*Last updated: 2026-06-14 after project initialization*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
