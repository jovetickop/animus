---
name: harness-cc
description: 复杂任务的编码工作流技能。输入 PRD+方案文档，自动拆解为可执行任务列表，按状态机逐个推进，验收后提交。支持 C++/Qt、Python、Node.js、Rust、Go。
---

## Hooks 配置

本技能注册了以下 Claude Code 钩子，用于维护状态完整性和验证：

| 钩子类型 | 触发时机 | 用途 |
|---------|---------|------|
| PreToolUse | Write/Edit 前 | 自动备份 features.json 防止写损坏 |
| PostToolUse | Write/Edit 后 | clang-format 自动格式化 C/C++ 文件 + format-all 多语言代码格式化 |
| PreCompact | 上下文压缩前 | 刷写当前进度到 claude-progress.txt |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 |

### 钩子行为说明

- **PreToolUse**：每次 Write/Edit 前备份 state/features.json → features.json.bak.时间戳（保留最近5份）
- **PreCompact**：在 claude-progress.txt 追加 [COMPACT] 标记行，报告当前任务完成进度
- **Stop**：检查所有任务的完成状态，输出未完成任务的恢复提示

### GBK 编码支持

针对 C/C++ 项目的 GBK 编码场景，harness 提供自动编码转换支持：

| 钩子阶段 | 转换方向 | 说明 |
|---------|---------|------|
| PreToolUse (Write/Edit前) | GBK → UTF-8 | 将 GBK 编码的源文件转为 UTF-8，确保 AI 正确读写 |
| PostToolUse (Write/Edit后) | UTF-8 → GBK | clang-format 格式化后自动转回 GBK，保持项目原始编码 |

在目标项目 `.claude/harness/project-config.json` 中设置 `"encoding": "gbk"` 即可启用。
详细说明见 `.claude/rules/cpp-cmake/encoding.md`。

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
2. 检测项目类型（CMakeLists.txt / Cargo.toml / go.mod / package.json / pyproject.toml）
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
| Go | `.claude/agents/go/architect.md` | `.claude/agents/universal/task-implementer.md` | `.claude/agents/go/test-engineer.md` |
| 其他 | — | `.claude/agents/universal/task-implementer.md` | `.claude/agents/universal/test-engineer.md` |

> **说明**：测试 agent 和实现 agent 的通用部分（输出格式、边界约束、验证要求等）已提取至 `agents/base/test-engineer-core.md` 和 `agents/base/task-implementer-core.md`。上表中的各语言 agent 仅保留语言专属内容，通用理论通过 HTML 注释引用对应基础文件。详细索引见 `agents/README.md`。

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

- 状态仅允许：`pending | in_progress | passed | failed | completed`（`completed` 是 `passed` 的别名，用于标记已通过且已关闭的任务）
- 同一 `parallel_group` 内只能有一个 `in_progress` 任务；不同 `parallel_group` 的任务可以并行执行；`parallel_group` 为空时视为默认组（完全串行）
- `parallel_group` 字段用于标记可并行执行的任务组，相同 group 的任务不可并行，不同 group 的任务可并发执行
- depends_on 必须满足才能开始
- 没有构建和测试结果，不得标记 `passed`
- 每轮必须更新 `claude-progress.txt`
- verify_command 必须由 Stop hook 或独立 Agent 执行，AI 不可修改
- passed 状态转换前必须运行 verify_command（如果配置）且 exit 0

## 核心文件

| 文件 | 用途 |
|------|------|
| `.claude/state/features.active.json` | 当前活动任务清单（pending/in_progress 任务） |
| `.claude/state/features.archive.json` | 已完成/失败任务归档 |
| `.claude/state/features.json` | 兼容旧版的任务清单（新项目使用 active/archive 拆分） |
| `.claude/state/claude-progress.txt` | 进度日志 |
| `.claude/harness/project-config.json` | 项目类型配置 |
| `SKILL.md` | 本文件 |

## 项目类型检测

按优先级检测：

1. `CMakeLists.txt` 含 `find_package(Qt` → `cpp-qt`
2. `CMakeLists.txt` 不含 Qt → `cpp-cmake`
3. `Cargo.toml` → `rust`
4. `go.mod` → `go`
5. `package.json` → `node`
6. `pyproject.toml` / `requirements.txt` → `python`
7. 以上都无 → `generic`

   > **注意**：对于 C/C++ 项目（cpp-cmake / cpp-qt），如果源文件使用 GBK 编码，请在 project-config.json 中设置 `"encoding": "gbk"`，hooks 会自动处理编码转换。

## MCP 集成

本技能支持以下 MCP 协议扩展，用于增强文件操作和状态追踪能力：

| MCP 工具 | 用途 |
|---------|------|
| Filesystem MCP | 用于读写 features.json 等状态文件，避免编码问题 |
| Memory MCP | 用于对 harness-history.jsonl 进行语义查询，分析失败模式和任务趋势 |

## 编码规范

参见：
- 通用规范：`.claude/rules/universal/coding-style.md`
- 测试规范：`.claude/rules/universal/testing.md`
- Git 规范：`.claude/rules/universal/git-workflow.md`
- 各语言最佳实践：`.claude/rules/{qt,python,node,rust,go}/best-practices.md`

