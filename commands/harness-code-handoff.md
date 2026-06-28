---
command: /harness-code-handoff
description: 保存当前 session 上下文快照到 handoff.json，供后续 session 恢复
---

# /harness-code-handoff

## 功能

收集当前会话上下文并保存到 `.claude/harness-cc/handoff.json`，供后续 `/harness-code-continue` 恢复。

当需要中断当前工作、关机或切换上下文时执行此命令，确保下次回来时能无缝恢复思路。

## 执行步骤

### 1. 加载当前状态

读取 `.claude/harness-cc/` 下的状态文件：

- `features.json` — 当前活动任务列表（含状态和验收标准）
- `task_plan.md` — 当前任务的子步骤计划
- `findings.md` — 已记录的决策和错误经验
- `feature-detail.md` — 当前任务的实现细节

### 2. 收集上下文信息

从加载的文件中提取以下信息：

- **当前任务**：features.json 中找到 status=in_progress 的任务 ID 和名称
- **当前子步骤**：task_plan.md 中最后一个未完成的 [ ] 子步骤
- **最近思考**：当前正在考虑的架构方案、实现策略或调试方向
- **最近决策**：已做出的设计决定（含被排除的替代方案）
- **待处理问题**：已知的阻塞项、待确认的 API 或待验证的假设
- **已读文件**：当前工作中已读取过的关键文件路径
- **下一步计划**：打算接下来做什么

### 3. 写入 handoff.json

将收集的信息写入 `.claude/harness-cc/handoff.json`，格式如下：

```json
{
  "session_id": "<8 字符随机十六进制>",
  "created_at": "2026-06-28T14:30:00",
  "status": "saved",
  "current_task_id": "I1-T003",
  "current_substep": "当前子步骤描述",
  "recent_thinking": [
    "正在考虑的架构方案 1",
    "正在调试的问题方向 2"
  ],
  "decisions": [
    {
      "topic": "决策主题",
      "decision": "确定的决策内容",
      "alternatives": ["被排除的方案 A"]
    }
  ],
  "pending_issues": [
    "待处理问题 1",
    "待处理问题 2"
  ],
  "key_files_read": [
    "src/main.cpp",
    "include/foo.h"
  ],
  "next_intended": "下一步的具体计划"
}
```

其中：
- `session_id`：生成随机 8 字符 hex 字符串
- `created_at`：当前时间，ISO 8601 格式
- `status`：固定为 `"saved"`

### 4. 更新 feature-detail.md

如果 `feature-detail.md` 存在，找到当前子步骤的 [ ] 标记，将其更新为 [x]。

### 5. 输出确认

完成输出：
```
Handoff 已保存: .claude/harness-cc/handoff.json
会话 ID: <session_id>
当前任务: <current_task_id> - <task_name>
状态: saved
下次使用 /harness-code-continue 恢复上下文
```
