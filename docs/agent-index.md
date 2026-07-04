# Agent 索引

本文档从 CLAUDE.md 迁移而来，列出所有 Agent 的目录位置和职责。

| 目录 | Agent | 显示名 | 副标题 | team | 职责 |
|------|-------|--------|--------|------|------|
| `agents/base/` | `task-implementer-core` | 实现者 (Core) | 多语言通用实现模板 | base | 通用任务实现核心 |
| | `test-engineer-core` | 测试官 (Core) | 多语言通用测试模板 | base | 通用测试理论核心 |
| `agents/universal/` | `feature-planner` | 规划师 (Plan) | 任务拆解与进度编排 | universal | PRD → features.json |
| | `task-implementer` | 实现者 (Impl) | 增量编码与构建修复 | universal | 单任务最小闭环实现 |
| | `test-engineer` | 测试官 (Test) | 测试方案设计与验证 | universal | 通用测试设计 |
| | `build-doctor` | 构建师 (Build) | 构建问题诊断与修复 | universal | 构建诊断 |
| | `code-reviewer` | 审查官 (Review) | 代码质量门控审查 | universal | 通用代码审查 |
| | `edge-case-hunter` | 边界猎手 | 空值/溢出/并发/资源泄露 | universal | 边界条件审查 |
| | `acceptance-auditor` | 验收审计官 | 验收条件逐条核对 | universal | 验收审计 |
| | `ponytail-reviewer` | 精简审查官 | 过度工程检查 | universal | 代码精简审查 |
| `agents/qt/` | `architect` | 架构师 (Qt) | Qt 类设计与架构决策 | qt | C++/Qt 架构 |
| | `task-implementer` | 实现者 (Qt) | Qt 增量编码实现 | qt | Qt 实现 |
| | `test-engineer` | 测试官 (Qt) | Qt 测试验证 | qt | Qt 测试 |
| | `ui-reviewer` | UI 审查官 (Qt) | Qt 界面可用性审查 | qt | Qt UI 审查 |
| `agents/cpp-cmake/` | `architect` | 架构师 (Cpp) | C++/CMake 构建方案设计 | cpp-cmake | 纯 C++ 架构 |
| `agents/python/` | `architect` | 架构师 (Py) | Python 架构设计与选型 | python | Python 架构 |
| | `test-engineer` | 测试官 (Py) | Python 测试方案 | python | Python 测试 |
| `agents/node/` | `architect` | 架构师 (Node) | Node/Web 架构设计与选型 | node | Web 架构 |
| | `test-engineer` | 测试官 (Node) | Node 测试方案 | node | Node 测试 |
| | `ui-reviewer` | UI 审查官 (Web) | 前端界面可用性审查 | node | 前端 UI 审查 |
| `agents/go/` | `architect` | 架构师 (Go) | Go 架构设计与选型 | go | Go 架构 |
| | `test-engineer` | 测试官 (Go) | Go 测试方案 | go | Go 测试 |
| `agents/rust/` | `architect` | 架构师 (Rust) | Rust 架构设计与选型 | rust | Rust 架构 |
| | `test-engineer` | 测试官 (Rust) | Rust 测试方案 | rust | Rust 测试 |
| `agents/frontend/` | `feature-planner-frontend` | 规划师 (FE) | 前端任务规划补充指南 | frontend | 前端任务规划 |

## 新增 Agent 规范

- Agent 文件位于 `agents/{lang}/` 目录，使用连字符命名（kebab-case）：`task-implementer.md`、`test-engineer.md`、`code-reviewer.md`。
- 新增 Agent 时需在 frontmatter 包含 `description` 字段——这是 Claude Code 触发 Agent 的关键匹配文本。
- 新增 Agent 描述要写明触发场景，否则 Claude Code 不会自动委派。
