---
description: 检测项目类型并复制对应工作流资产到目标工程
---

# /code-setup

## 目标

- 安装 `.claude/harness/`，让项目可以跨会话保存任务状态
- 自动检测项目类型
- 按检测结果复制对应的 agent 和 rule 插件
- 自动探索构建/测试/运行命令，写入根目录 CLAUDE.md

## 模板源目录

模板资产位于技能目录（SKILL.md 所在目录）下。直接从技能目录读取 assets。

## 检测逻辑

按优先级依次检查目标项目根目录的以下文件：

1. **CMakeLists.txt** → 检测是否含 Qt
   - 包含 `find_package(Qt` → project-type = `cpp-qt`
   - 不含 Qt → project-type = `cpp-cmake`
2. **Cargo.toml** → project-type = `rust`
3. **package.json** → project-type = `node`
4. **pyproject.toml** 或 **requirements.txt** → project-type = `python`
5. 以上都无 → project-type = `generic`

检测完成后，将 project-type 写入目标项目 `.claude/harness/project-config.json`。

## 复制策略

### 始终复制

| 来源（技能目录） | 目标（项目） | 说明 |
|------|------|------|
| `templates/harness/` → | `.claude/harness/` | 长任务状态管理工具集 |
| `agents/universal/` → | `.claude/agents/universal/` | 通用 Agent |
| `rules/universal/` → | `.claude/rules/universal/` | 通用规范 |
| `commands/` → | `.claude/commands/` | 斜杠命令 |
| `skills/tdd-workflow/` → | `.claude/skills/tdd-workflow/` | TDD 工作流 skill |
| `hooks/` → | `.claude/hooks/` | 自动化钩子 |
| `templates/existing_project/CLAUDE.md` → | `./CLAUDE.md` | 合并到项目 CLAUDE.md |
| `templates/existing_project/review-checklist.md` → | `./review-checklist.md` | 验收清单 |
| `templates/existing_project/cmake-adapter.md` → | `./cmake-adapter.md` | CMake 接入说明 |
| `templates/.clang-format` → | `./.clang-format` | C++ 格式化配置 |
| `templates/.mcp.json` → | `./.mcp.json` | MCP 服务器配置 |

### 按类型复制

| project-type | agents 源 | rules 源 |
|---|---|---|
| `cpp-qt` | `agents/qt/` → `.claude/agents/qt/` | `rules/qt/` → `.claude/rules/qt/` |
| `cpp-cmake` | 无专项 | 无专项 |
| `python` | `agents/python/` → `.claude/agents/python/` | `rules/python/` → `.claude/rules/python/` |
| `node` | `agents/node/` → `.claude/agents/node/` | `rules/node/` → `.claude/rules/node/` |
| `rust` | `agents/rust/` → `.claude/agents/rust/` | `rules/rust/` → `.claude/rules/rust/` |
| `generic` | 无专项 | 无专项 |

### CLAUDE.md 合并策略

目标项目已有 CLAUDE.md 时：
- **不覆盖**原有内容
- **追加** CodeHarness 区块到文件末尾
- 如已有 CodeHarness 区块，更新而非重复

## 输出要求

始终报告：

- 检测到的项目类型
- 已复制或生成的文件清单
- 构建命令、测试命令、运行命令
- 需要人工确认的事项

## 安全规则

- 不覆盖目标工程已有源码
- 目标工程已有 `.claude/` 内容时，合并保留不相关配置
- 不修改目标工程的构建脚本或业务代码
