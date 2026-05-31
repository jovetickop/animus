---
name: harness-cc
description: 复杂任务的编码工作流技能。输入 PRD+方案文档，自动拆解为可执行任务列表，按状态机逐个推进，验收后提交。支持 C++/Qt、Python、Node.js、Rust。
---

# CodeHarness — 编码工作流技能

## 适用场景

- 需要多轮编码会话的复杂功能开发
- 跨上下文的任务持久化（今天做完，明天继续）
- 需要严格验收流程的项目（构建+测试+审查+提交）

## 首次使用

在目标项目中执行 `/harness-cc`，技能会自动检测状态：

### 如果目标项目没有 `.claude/harness/`

技能从自身目录复制 harness 模板到目标项目：

1. 复制 `.claude/templates/harness/` → `.claude/harness/`（状态引擎脚本）
2. 检测项目类型（CMakeLists.txt / Cargo.toml / package.json / pyproject.toml）
3. 在目标项目创建 `.claude/agents/`、`.claude/commands/`、`.claude/rules/` 目录，按需复制插件
4. 将合适的 CLAUDE.md 模板写入目标项目根目录
5. 将检测到的构建/测试命令写入 target CLAUDE.md

### 如果目标项目已有 `.claude/harness/`

直接进入工作流。

## 工作流

### Step 1: 读取状态

```
python .claude/harness/show-status.py
Get-Content .claude/state/claude-progress.txt -Tail 20
```

### Step 2: 选择任务

- 优先继续 `in_progress` 任务
- 否则选择依赖已满足且 priority 最高的 `pending` 任务
- 无任务时执行 `/harness-code-plan` 从 PRD/方案拆解（/harness-code-plan 内部使用 `.claude/agents/universal/feature-planner.md` 生成 features.json）

### Step 3: 标记任务开始

```
.\.claude\harness\update-progress.ps1 <TaskId> in_progress "说明"
```

### Step 4: 实现

根据 `project-type` 选择 agent：

| 语言 | 架构 agent | 实现 agent | 测试 agent |
|------|-----------|-----------|-----------|
| C++/Qt | `.claude/agents/qt/architect.md` | `.claude/agents/qt/task-implementer.md` | `.claude/agents/qt/test-engineer.md` |
| C++ (纯 CMake) | `.claude/agents/cpp-cmake/architect.md` | `.claude/agents/universal/task-implementer.md` | `.claude/agents/universal/test-engineer.md` |
| Python | `.claude/agents/python/architect.md` | `.claude/agents/universal/task-implementer.md` | `.claude/agents/python/test-engineer.md` |
| Node | `.claude/agents/node/architect.md` | `.claude/agents/universal/task-implementer.md` | `.claude/agents/node/test-engineer.md` |
| Rust | `.claude/agents/rust/architect.md` | `.claude/agents/universal/task-implementer.md` | `.claude/agents/rust/test-engineer.md` |
| 其他 | — | `.claude/agents/universal/task-implementer.md` | `.claude/agents/universal/test-engineer.md` |

构建失败时使用 `.claude/agents/universal/build-doctor.md`。UI 改动使用对应语言的 `ui-reviewer`。

### Step 5: 代码审查

在构建/测试之前，使用 `.claude/agents/universal/code-reviewer.md` 对本次变更进行审查：

- 代码质量：命名、嵌套深度、错误处理、魔法数字
- 测试覆盖：新增行为是否有对应测试
- 安全性：硬编码密钥、输入校验
- 变更影响：是否波及无关模块

按输出严重级别处理：**critical/high** 必须修复后才能继续，**medium/low** 记录待办后可继续。

### Step 6: 验证

执行 CLAUDE.md 中的构建命令和 features.json 中的 test_command。
可用 `.claude/harness/run-regression.ps1` 一键执行构建+测试。

### Step 7: 验收

执行 `/harness-code-review`：通用检查（构建+测试+代码质量）+ 语言专项检查。

### Step 8: 完成或失败

- 通过：`.\.claude\harness\update-progress.ps1 <TaskId> passed "说明"`
- 失败：`.\.claude\harness\update-progress.ps1 <TaskId> failed "原因"`
- 每个任务完成后提交：按 `.claude/rules/universal/git-workflow.md` 执行

## 状态规则

- 状态仅允许：`pending | in_progress | passed | failed`
- 同时只能有一个 `in_progress` 任务
- depends_on 必须满足才能开始
- 没有构建和测试结果，不得标记 `passed`
- 每轮必须更新 `claude-progress.txt`

## 核心文件

| 文件 | 用途 |
|------|------|
| `.claude/state/features.json` | 任务清单与状态 |
| `.claude/state/claude-progress.txt` | 进度日志 |
| `.claude/harness/project-config.json` | 项目类型配置 |
| `SKILL.md` | 本文件 |

## 项目类型检测

按优先级检测：

1. `CMakeLists.txt` 含 `find_package(Qt` → `cpp-qt`
2. `CMakeLists.txt` 不含 Qt → `cpp-cmake`
3. `Cargo.toml` → `rust`
4. `package.json` → `node`
5. `pyproject.toml` / `requirements.txt` → `python`
6. 以上都无 → `generic`

## 编码规范

参见：
- 通用规范：`.claude/rules/universal/coding-style.md`
- 测试规范：`.claude/rules/universal/testing.md`
- Git 规范：`.claude/rules/universal/git-workflow.md`
- 各语言最佳实践：`.claude/rules/{qt,python,node,rust}/best-practices.md`
