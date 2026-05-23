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

模板资产默认位于本仓库的 `.claude/` 目录下。直接从当前 `.claude/` 目录中读取 assets，不要要求用户手动复制文件。

如果当前工作目录不是模板仓库根目录，优先从以下位置查找模板源：

1. `.claude/` 存在且包含 `templates/harness/features.json` → 当前目录即为模板源
2. 显式指定的路径
3. 提示用户确认或手动指定

找到模板源后，统一以模板源目录下的 `.claude/` 作为资产根目录。

## 检测逻辑

按优先级依次检查以下文件是否存在：

1. **CMakeLists.txt**（项目根目录）→ 检测是否含 Qt
   - 用文本搜索检查文件内容是否包含 `find_package(Qt` → project-type = `cpp-qt`
   - 不含 Qt → project-type = `cpp-cmake`
2. **Cargo.toml** 存在 → project-type = `rust`
3. **package.json** 存在 → project-type = `node`
4. **pyproject.toml** 或 **requirements.txt** 存在 → project-type = `python`
5. 以上都无 → project-type = `generic`

检测完成后，将 project-type 写入 `.claude/harness/project-config.json` 以备后续命令使用。

## 复制策略

### 始终复制（不覆盖已有文件）

| 来源 | 目标 | 说明 |
|------|------|------|
| `templates/harness/` → | `.claude/harness/` | 长任务状态管理工具集 |
| `agents/universal/` → | `.claude/agents/universal/` | 通用 Agent（feature-planner, task-implementer, test-engineer, build-doctor, code-reviewer） |
| `rules/universal/` → | `.claude/rules/universal/` | 通用规范（coding-style, testing, git-workflow） |
| `commands/` → | `.claude/commands/` | 斜杠命令（code-plan, code-check, code-setup） |
| `skills/tdd-workflow/` → | `.claude/skills/tdd-workflow/` | TDD 工作流 skill |
| `hooks/` → | `.claude/hooks/` | 自动化钩子（hooks.json + clang-format 脚本） |
| `templates/existing_project/CLAUDE.md` → | `/CLAUDE.md` | 根 CLAUDE.md 模板（填入实际命令） |
| `templates/existing_project/review-checklist.md` → | `/review-checklist.md` | 验收清单 |
| `templates/existing_project/cmake-adapter.md` → | `/cmake-adapter.md` | CMake 接入说明 |
| `templates/.clang-format` → | `/.clang-format` | C++ 格式化配置 |
| `templates/.mcp.json` → | `/.mcp.json` | MCP 服务器配置 |

### 按类型复制（目录存在时复制）

根据检测到的 `project-type`：

| project-type | agents 源 | rules 源 |
|---|---|---|
| `cpp-qt` | `agents/qt/` → `.claude/agents/qt/` | `rules/qt/` → `.claude/rules/qt/` |
| `cpp-cmake` | 无专项 agent | 无专项 rule |
| `python` | `agents/python/` → `.claude/agents/python/` | `rules/python/` → `.claude/rules/python/` |
| `node` | `agents/node/` → `.claude/agents/node/` | `rules/node/` → `.claude/rules/node/` |
| `rust` | `agents/rust/` → `.claude/agents/rust/` | `rules/rust/` → `.claude/rules/rust/` |
| `generic` | 无专项 agent | 无专项 rule |

### 不覆盖原则

- 不覆盖目标工程中已有的 `src/`、`include/`、`ui/`、`tests/` 等源码目录
- `.claude/` 目录下已有但与模板不冲突的文件必须保留
- 复制时对每个文件先检查目标是否存在，存在则跳过

## 自动探索命令

始终执行以下步骤：

1. **收集候选命令**：
   - 优先读取 `CMakePresets.json`、`CMakeUserPresets.json`（仅 C++ 项目）
   - 读取已有构建脚本（`build*.ps1`、`build*.bat`、`build*.sh`、`Makefile`）
   - 读取已有测试脚本（`test*.ps1`、`test*.bat`、`test*.sh`）
   - 按项目类型的回退候选：
     - cpp-qt / cpp-cmake：`cmake -S . -B build && cmake --build build --config Debug`
     - rust：`cargo build` / `cargo test`
     - node：`npm run build` / `npm test`
     - python：`pip install -e .` / `pytest`

2. **验证候选命令**：至少成功执行一次配置（或等价初始化）和构建命令。

3. **有测试入口时**：至少执行一次测试或 smoke test。

4. **写入 CLAUDE.md**：将最终验证通过的命令写入目标工程根目录 `CLAUDE.md` 的"自动识别命令"区块，禁止留空占位符。

5. **检查 Git 仓库**：`git rev-parse --is-inside-work-tree` 确认是否受版本控制。

6. **失败处理**：如果某项无法探测成功，写明失败原因、已尝试命令和推荐下一步。

## 输出要求

始终报告以下内容：

- 检测到的项目类型（`cpp-qt` / `cpp-cmake` / `rust` / `node` / `python` / `generic`）
- 已复制或生成的文件清单
- 构建命令（已验证 / 未验证）
- 测试命令（已验证 / 未验证 / 不可用及原因）
- 运行命令（如可探测）
- 是否为 Git 仓库
- 需要人工确认的事项

## 安全规则

- 未经明确同意，不覆盖目标工程中的 `src/`、`include/`、`ui/`、`tests/` 等源码目录
- 如果目标工程已有 `.claude/` 内容，合并时必须保留不相关配置，只添加/更新模板资产
- 不自作主张修改目标工程的业务代码、CMakeLists.txt 或项目配置
- 不对目标工程执行破坏性操作（如 `git reset`、文件删除等）
