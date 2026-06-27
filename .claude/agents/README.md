# Agent 索引

| 路径 | 角色 | 语言范围 | 引用基础文件 |
|------|------|---------|------------|
| `universal/feature-planner.md` | 任务规划 | 全语言 | — |
| `frontend/feature-planner-frontend.md` | 前端任务规划 | 前端 (React/Vue) | `universal/feature-planner.md` |
| `universal/task-implementer.md` | 任务实现 | 通用（CMake/其他） | `base/task-implementer-core.md` |
| `qt/task-implementer.md` | 任务实现 | C++/Qt | `base/task-implementer-core.md` |
| `universal/test-engineer.md` | 测试设计 | 通用（CMake/其他） | `base/test-engineer-core.md` |
| `qt/test-engineer.md` | 测试设计 | C++/Qt | `base/test-engineer-core.md` |
| `python/test-engineer.md` | 测试设计 | Python | `base/test-engineer-core.md` |
| `node/test-engineer.md` | 测试设计 | Node.js/Web | `base/test-engineer-core.md` |
| `rust/test-engineer.md` | 测试设计 | Rust | `base/test-engineer-core.md` |
| `go/test-engineer.md` | 测试设计 | Go | `base/test-engineer-core.md` |
| `universal/code-reviewer.md` | 代码审查 | 全语言 | — |
| `universal/build-doctor.md` | 构建诊断 | 全语言 | — |
| `cpp-cmake/architect.md` | 架构设计 | C++ (CMake) | — |
| `qt/architect.md` | 架构设计 | C++/Qt | — |
| `python/architect.md` | 架构设计 | Python | — |
| `node/architect.md` | 架构设计 | Node.js | — |
| `rust/architect.md` | 架构设计 | Rust | — |
| `go/architect.md` | 架构设计 | Go | — |
| `qt/ui-reviewer.md` | UI 审查 | Qt Widgets | — |
| `node/ui-reviewer.md` | UI 审查 | React/Vue/Web | — |
| `base/test-engineer-core.md` | 测试核心 | 参考文件 | — |
| `base/task-implementer-core.md` | 实现核心 | 参考文件 | — |

## 文件层级说明

- `base/` — 基础核心文件，被各语言专属文件引用，不单独使用
- `universal/` — 跨语言通用 agent，可直接使用
- `{lang}/` — 语言专属 agent，需配合 `universal/` 或 `base/` 使用
- `frontend/` — 前端专属补充文件，被 `universal/feature-planner.md` 引用
