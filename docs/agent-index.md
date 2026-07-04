# Agent 索引

本文档从 CLAUDE.md 迁移而来，列出所有 Agent 的目录位置和职责。

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

## 新增 Agent 规范

- Agent 文件位于 `agents/{lang}/` 目录，使用连字符命名（kebab-case）：`task-implementer.md`、`test-engineer.md`、`code-reviewer.md`。
- 新增 Agent 时需在 frontmatter 包含 `description` 字段——这是 Claude Code 触发 Agent 的关键匹配文本。
- 新增 Agent 描述要写明触发场景，否则 Claude Code 不会自动委派。
