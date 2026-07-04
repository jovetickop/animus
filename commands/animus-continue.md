---
command: /animus-continue
description: 从 handoff.json 恢复上次 session 的上下文
---

# /animus-continue

## 功能

读取 `.claude/animus/handoff.json`，恢复上次 `/animus-handoff` 保存的会话上下文。

与 `/animus-handoff` 互为逆向操作。

## 执行步骤

### 1. 读取 handoff.json

读取 `.claude/animus/handoff.json`。如果文件不存在，提示"未找到 handoff.json，请先执行 /animus-handoff"并结束。

### 2. 检查状态

检查 `status` 字段：

- `"loaded"` — 输出"Handoff 已加载过，当前进度已恢复"，跳过后续恢复步骤
- `"saved"` — 继续执行恢复，完成后将 status 改为 `"loaded"`
- 其他值 — 提示异常状态，仍尝试恢复

### 3. 加载相关状态文件

同时加载 `/animus-continue` 补充读取以下文件：

```
.claude/animus/features.json          — 任务列表和状态
.claude/animus/animus-history.jsonl   — 状态转换历史
.claude/animus/task_plan.md            — 子步骤进度计划
.claude/animus/findings.md             — 决策和错误经验
.claude/animus/feature-detail.md       — 当前任务实现细节
```

### 4. 输出恢复报告

按以下格式输出恢复结果：

```
上下文恢复完成
上次工作: <next_intended>
当前任务: <current_task_id> - <task_name>
进度: <current_substep>
待处理: <pending_issues>
```

### 5. 标记已加载

将 handoff.json 的 `status` 字段改为 `"loaded"` 并写回文件，防止重复加载。

### 6. 建议下一步

根据恢复的上下文，结合当前 features.json 中的任务状态，给出下一步具体操作建议（如"继续实现 T003 的步骤 3"、"修复 T002 的构建失败"等）。
