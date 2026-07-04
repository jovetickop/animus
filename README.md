# animus

`animus` 是一个 Claude Code 插件，面向**需要多轮编码会话的复杂任务**。它是一个**编码工作流引擎**——任务拆解编排、进度持久化、JSONL 日志追踪、跨会话上下文恢复、自动代码审查门控、系统化调试工作流。

---

## 安装

```
/plugin marketplace add jovetickop/animus
/plugin install animus@animus
```

安装后可用七条斜杠命令：

| 命令 | 什么时候用 |
|------|-----------|
| `/animus-setup` | 首次接入：初始化目标项目的运行时状态 |
| `/animus-plan` | 有新需求：PRD/方案 → 可执行任务列表 |
| `/animus-debug` | 遇到 Bug：系统化调试（根因调查→分析→修复→规划→审查） |
| `/animus-review` | 实现完成：通用 + 语言专项验收检查 |
| `/animus-handoff` | session 结束时：保存上下文快照到 handoff.json |
| `/animus-continue` | 新 session 中：从 handoff.json 恢复上下文 |
| `/animus-archive` | 阶段完成时：归档当前迭代，清空并开始新迭代 |

日常开发：`/animus-plan`（拆任务）→ 实现 → `/animus-review`（验收）
调试修复：`/animus-debug`（根因→修复→规划→审查）

---

## 为什么要用状态机？

Claude Code 做长周期开发有几个硬伤，animus 的解法：

| 问题 | 解法 |
|------|------|
| **跨会话失忆** | 每次启动读 `features.json` + `animus-history.jsonl` + `task_plan.md`，恢复现场 |
| **一口气改太多** | 每轮只推进一个任务，不越界 |
| **过早宣布完成** | 硬规则：没有构建/测试证据，不得标记 `passed` |
| **会话中断恢复困难** | 5 问重启检查：`python scripts/session-catchup.py --project-dir .` |
| **验证流程依赖人工** | Oracle 门控：标记 `passed` 前自动执行 `verify_command`，不通过自动退回 `failed` |
| **任务进度太粗** | `task_plan.md` 子步骤追踪 + `findings.md` 知识积累 |

---

## 工作流（8 步闭环）

| 步骤 | 动作 |
|------|------|
| 1 | 读取 `features.json` + `animus-history.jsonl`，判断当前阶段 |
| 2 | 优先继续 `in_progress` 任务，否则选依赖满足且 priority 最高的 `pending` |
| 3 | `update-progress.ps1 T001 in_progress "开始实现登录模块"` |
| 4 | 按 project-type 对应语言 agent 实现 |
| 5 | 代码审查：命名、嵌套、错误处理、测试覆盖 |
| 6 | 构建 + 测试（`run-regression.ps1` 一键执行） |
| 7 | `/animus-review` 终验 |
| 8 | `update-progress.ps1 T001 passed "完成"` 或 `... T001 failed "原因"`，提交 |

---

## 状态流转

```
pending → in_progress → passed → completed（别名）
                    └→ failed → in_progress（重试）
```

- `pending → in_progress`：检查 depends_on 全部 `passed`
- `in_progress → passed`：自动执行 Oracle 验证门控
- `in_progress → failed`：必须提供原因
- 硬规则：无构建/测试证据不得 `passed`；失败任务保持 `failed` 不自动回退

---

## 三层架构

```
┌─ 插件入口 ──────────────────────────────┐
│  .claude-plugin/plugin.json              │
├─ 编排层 ────────────────────────────────┤
│  /animus-setup  /animus-plan │
│  /animus-review                    │
├─ 执行层 ────────────────────────────────┤
│  agents/{universal,qt,python,node,rust}  │
│  rules/{universal,qt,python,node,rust}   │
├─ 持久化层 ──────────────────────────────┤
│  features.json  animus-history.jsonl    │
│  task_plan.md   findings.md             │
├─ 运行时引擎 ─────────────────────────────┤
│  update-progress.ps1（薄编排器）           │
│  modules/（5 领域模块）                    │
└─────────────────────────────────────────┘
```

---

## 项目类型检测

```
CMakeLists.txt├── Qt → cpp-qt
              └── 无 Qt → cpp-cmake
Cargo.toml                  → rust
go.mod                      → go
package.json                → node
pyproject.toml/requirements  → python
都检测不到                   → generic
```

---

## 快捷使用

```bash
# 查看状态
.\.claude\animus\show-status.ps1

# 会话恢复（/clear 后用）
python scripts/session-catchup.py --project-dir .

# 验证 features.json 结构
.\.claude\animus\validate-features.ps1
```

---

## Hooks（4 个自动化钩子）

| Hook | 触发时机 | 作用 |
|------|---------|------|
| PreToolUse | Write/Edit 前 | 备份 features.json；GBK→UTF-8 转码 |
| PostToolUse | Write/Edit 后 | clang-format 格式化；format-all.py 多语言格式化；UTF-8→GBK 回转 |
| PreCompact | 上下文压缩前 | JSONL compact 事件 + task_plan.md 自动同步 |
| Stop | 会话结束时 | 检查未完成任务，输出中文提示 |

全部 `exit 0` 不阻塞主流程，双平台（.ps1 + .sh）互为降级。

---

## 目录结构（核心）

```
├── agents/{universal,qt,cpp-cmake,python,node,rust,go}/
├── commands/{animus-setup,plan,review}
├── rules/{universal,qt,cpp-cmake,python,node,rust,go}/
├── hooks/hooks.json + scripts/
├── scripts/session-catchup.py
├── skills/tdd-workflow/
└── templates/animus/ + existing_project/
```

### 状态文件
| 文件 | 用途 |
|------|------|
| `features.json` | 任务状态 + 依赖（纯数组，仅机器读） |
| `feature-detail.md` | 功能方案文档（详细描述"怎么做"） |
| `animus-history.jsonl` | 结构化日志 |
| `task_plan.md` | 子步骤追踪 |
| `findings.md` | 知识积累（决策/错误/待办） |
| `domain-lexicon.md` | 领域术语表 |
| `adr/` | 架构决策记录 |

完整结构见仓库 `CLAUDE.md`。
