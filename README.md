# animus

Claude Code 编码工作流引擎。面向复杂多轮编码任务——任务拆解编排、进度持久化、JSONL 日志追踪、跨会话恢复、自动审查门控、系统化调试。

---

## 安装

```
/plugin marketplace add jovetickop/animus
/plugin install animus@animus
```

安装后可用七条斜杠命令：

| 命令 | 用途 |
|------|------|
| `/animus-setup` | 初始化目标项目运行时状态 |
| `/animus-plan` | PRD/方案 → 可执行任务列表 |
| `/animus-debug` | 系统化调试（根因→分析→修复→审查） |
| `/animus-review` | 通用 + 语言专项验收 |
| `/animus-handoff` | 保存 session 上下文快照 |
| `/animus-continue` | 从 handoff.json 恢复上下文 |
| `/animus-archive` | 归档当前迭代，清空开始新迭代 |

日常流程：`/animus-plan` → 实现 → `/animus-review`
调试流程：`/animus-debug`

---

## 为什么用状态机？

| 痛点 | 解法 |
|------|------|
| 跨会话失忆 | `features.json` + `animus-history.jsonl` + `task_plan.md` 恢复现场 |
| 一口气改太多 | 每轮只推进一个任务，不越界 |
| 过早宣布完成 | 硬规则：无构建/测试证据不得 `passed` |
| 会话中断恢复难 | `session-catchup.py` 五问重启检查 |
| 验证依赖人工 | Oracle 门控：自动执行 `verify_command`，不通过退回 `failed` |
| 任务粒度太粗 | `task_plan.md` 子步骤 + `findings.md` 知识积累 |

## 状态流转

```
pending → in_progress → passed
                    └→ failed → in_progress（重试）
```

- `pending → in_progress`：前置依赖全部 `passed`
- `in_progress → passed`：自动 Oracle 验证门控
- `in_progress → failed`：必须提供原因
- 硬规则：无构建/测试证据不得 `passed`

---

## 架构

```
插件清单 → 编排命令 → 执行层（Agent + Rule）
         → 持久化层（features.json, JSONL, task_plan.md）
         → 运行时引擎（update-progress.ps1 + 5 领域模块）
```

### 项目类型检测

```
CMakeLists.txt → Qt → cpp-qt / 无 Qt → cpp-cmake
Cargo.toml     → rust   go.mod     → go
package.json   → node   pyproject   → python
都检测不到     → generic
```

### Hooks（4 个自动化钩子，全部 `exit 0` 不阻塞）

| Hook | 触发时机 | 作用 |
|------|---------|------|
| PreToolUse | Write/Edit 前 | 备份 features.json；GBK→UTF-8 |
| PostToolUse | Write/Edit 后 | clang-format；format-all 多语言格式化；UTF-8→GBK |
| PreCompact | 上下文压缩前 | JSONL compact 事件 + task_plan 同步 |
| Stop | 会话结束时 | 检查未完成任务，输出提示 |

---

## 快捷使用

```bash
# 查看状态
.\.claude\animus\show-status.ps1

# 会话恢复（/clear 后）
python scripts/session-catchup.py --project-dir .

# 验证 features.json 结构
.\.claude\animus\validate-features.ps1
```

## 核心状态文件

| 文件 | 用途 |
|------|------|
| `features.json` | 任务状态 + 依赖（纯数组，机器读写） |
| `animus-history.jsonl` | 结构化操作日志 |
| `task_plan.md` | 子步骤追踪 |
| `findings.md` | 知识积累（决策/错误/待办） |
| `domain-lexicon.md` | 领域术语表 |
| `feature-detail.md` | 功能方案文档 |
| `adr/` | 架构决策记录 |
