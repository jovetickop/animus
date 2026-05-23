# ty-qt-ai-plugin 功能清单

> 系统化盘点模板工作流的所有已支持功能。

---

## 一、任务状态引擎（Harness）

用于跨会话管理长任务的生命周期。

| 功能 | 文件 | 说明 |
|------|------|------|
| **状态机** | `update-progress.ps1` | `pending → in_progress → passed/failed`，严格校验流转合法性 |
| **依赖管理** | `update-progress.ps1` | `depends_on` 前置检查：确保依赖已 `passed` 且任务 ID 存在 |
| **冲突检测** | `update-progress.ps1` | 阻止同时存在多个 `in_progress` 任务 |
| **AutoPush** | `update-progress.ps1` | 可选 `-AutoPush` 参数，状态变更后自动 git commit + push |
| **进度日志** | `claude-progress.txt` | 追加写入 `时间戳 \| ID \| 旧状态 → 新状态 \| 说明` |
| **自动报告** | `update-progress.ps1` | 每次状态流转自动生成 `docs/reports/<TaskId>-<name>.md` |
| **状态概览** | `show-status.py` | 输出：总数/通过/失败/进行中/下一个可执行/被阻塞数 |
| **BAT 包装** | `*.bat` | 所有 PS1 脚本都有同名的 `.bat` 包装，CMD 下直接调用 |

**状态流转规则：**

```
pending ──→ in_progress
in_progress ──→ passed
in_progress ──→ failed
failed ──→ in_progress (重试)
failed ──→ pending (仅人工确认后可重排)
```

---

## 二、会话管理

| 入口 | 文件 | 用途 |
|------|------|------|
| **初始化** | `init.ps1` / `init.bat` | 首次运行：创建 harness 目录、检查 features.json |
| **会话开始** | `coding-session.ps1` / `coding-session.bat` | 每次编码会话入口，加载当前任务概览 |
| **一键回归** | `run-regression.ps1` | 顺序执行 `cmake --build` + `ctest` |

---

## 三、Agent 角色（6 个）

每个 Agent 是独立的 `.md` 定义文件，位于 `.claude/agents/`：

| Agent | 职责 | 解决什么问题 |
|-------|------|-------------|
| `harness-feature-planner` | 把 PRD 拆成可执行的小任务 | 需求 → features.json |
| `qt-architect` | 编码前评估类设计、生命周期、线程风险 | "这么做会踩什么坑" |
| `qt-task-implementer` | 单任务最小闭环实现 | 一次只做一个任务，不越界 |
| `qt-test-engineer` | 设计测试矩阵、补 test_command | 测试覆盖不够怎么办 |
| `qt-ui-reviewer` | 审查布局、sizePolicy、反馈、文案 | 界面可用性把关 |
| `cmake-build-doctor` | 诊断 CMake/Qt 构建失败 | 构建挂了怎么办 |

---

## 四、斜杠命令（3 个）

位于 `.claude/commands/`：

### `/setup`
- 自动识别 **新工程** / **存量工程** 两种模式
- 新工程：复制模板骨架、替换占位符
- 存量工程：只补 `.claude/` 配置，不改已有源码
- 自动探测：`cmake -S . -B build` → `cmake --build build` → `ctest`
- 将探测结果写入根目录 `CLAUDE.md`

### `/plan`
- 将 PRD 转为 `features.json` 任务列表
- 自动包含：`id`、`name`、`depends_on`、`priority`、`test_command`、`acceptance_criteria`
- 规则：Qt UI 优先、依赖链正确、粒度够小

### `/review`
- 四类验收检查：
  - 构建正确性
  - 测试覆盖
  - Qt 风险（QObject 所有权、线程、信号槽、MOC/UIC/RCC）
  - UI 质量（布局、sizePolicy、反馈、文案）
- 输出严重级别：high / medium / low
- 验证 harness 状态一致性

---

## 五、编码规范（5 份规则文件）

位于 `.claude/rules/`：

| 规则文件 | 覆盖内容 |
|----------|---------|
| `coding-style.md` | PascalCase/蛇形命名、4 空格、头文件结构、include 顺序、中文注释、`const` 约束、immutability |
| `testing.md` | 80% 基线、四类用例（正常/空/无效/边界）、构建+测试通过才标记完成 |
| `git-workflow.md` | Conventional Commits、中文描述、提交前检查清单 |
| `qt-best-practices.md` | QObject 父子关系、新式信号槽语法、非主线程不操作 UI、RAII |
| `ui-architecture.md` | 布局优先、面板边界、按钮位置和反馈、无歧义文案 |

---

## 六、自动化钩子

位于 `.claude/hooks/`：

| 触发时机 | 匹配工具 | 动作 |
|---------|----------|------|
| **PostToolUse** | `Write\|Edit` | 对 `.cpp\|.cc\|.cxx\|.c\|.h\|.hpp\|.hxx` 文件自动执行 `clang-format` |
| **双后备** | — | Bash 优先，失败则退到 PowerShell |

---

## 七、模板资产总览（`templates/`）

位于 `.claude/templates/`：

| 类别 | 文件 | 说明 |
|------|------|------|
| **构建入口** | `existing_project/CLAUDE.md` | 存量工程适配模板 |
| **存量工程** | `existing_project/review-checklist.md` | 验收检查清单 |
| **存量工程** | `existing_project/cmake-adapter.md` | 接入原则说明 |

---

## 八、存量工程模板（`existing_project`）

位于 `.claude/templates/existing_project/`：

| 文件 | 说明 |
|------|------|
| `CLAUDE.md` | 会话初始化、状态流转、开发验收、Git 提交的完整约束 |
| `review-checklist.md` | 6 条验收检查项 |
| `cmake-adapter.md` | 核心原则：工作流适配工程，不是工程适配工作流 |

---

## 九、MCP 集成

位于 `.claude/templates/.mcp.json`：

| 服务器 | 类型 | 用途 |
|--------|------|------|
| `filesystem` | stdio | 安全文件系统访问 |
| `git` | stdio | Git 仓库操作 |
| `memory` | stdio | 知识图谱持久化 |

---

## 十、TDD 工作流

位于 `.claude/skills/tdd-workflow/SKILL.md`：

| 能力 | 说明 |
|------|------|
| **C++/Qt TDD 闭环** | RED → GREEN → IMPROVE |
| **测试框架覆盖** | GoogleTest（纯 C++）+ QTest（Qt Core/UI）+ CTest 集成 |
| **异步测试模式** | QSignalSpy、QTRY_VERIFY、超时保护 |
| **测试类型指南** | 纯逻辑 / Qt Core / Qt UI 三种粒度的测试策略 |
| **常见错误对照** | 6 组错误 vs 正确做法（sleep、测试私有实现、手工验证等） |

---

## 十一、基础设施

| 资产 | 文件 | 说明 |
|------|------|------|
| **格式配置** | `.clang-format` | C++ 格式化规则 |
| **Git 忽略** | （建议 `build/`、`bin/`、`CMakeUserPresets.json`） | 随 `/setup` 补充 |
| **Settings** | `.claude/settings.local.json` | 项目级权限白名单 |
| **README** | 仓库根 `README.md` | 插件架构和使用说明 |

---

## 统计一览

| 类别 | 数量 |
|------|------|
| Agent 定义 | 6 |
| 斜杠命令 | 3 |
| 规则文件 | 5 |
| 钩子规则 | 1（PostToolUse） |
| 模板文件（existing_project） | 3 |
| 模板文件（harness） | 10（PS1 + BAT + py） |
| Skill | 1（TDD） |
| MCP 服务器默认配置 | 3 |
| **总计资产文件** | **~35+** |
