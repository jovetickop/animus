---
description: 将 PRD 转为 harness 任务列表，并更新 .claude/harness/features.json
---

请把当前 PRD 或需求整理成可执行任务列表。

## 目标

- 以 PRD 作为唯一范围依据。
- 产出可支撑“一次一个任务”执行的任务列表。
- 让结果与 `.claude/harness/features.json` 保持同步。
- 为每个任务补齐显式验收与测试命令。

## 输出格式约束

更新或创建 `.claude/harness/features.json`，任务结构如下：

```json
[
  {
    "id": "T001",
    "name": "Create the main window skeleton",
    "status": "pending",
    "depends_on": [],
    "priority": 100,
    "test_command": "ctest --test-dir build -R T001_MainWindowSmoke --output-on-failure",
    "last_error": "",
    "updated_at": "",
    "acceptance_criteria": [
      "The main window launches successfully",
      "The menu bar and central workspace exist",
      "The smoke test passes"
    ]
  }
]
```

## 规划规则

1. 任务必须基于当前 PRD，不要凭空扩展。
2. 任务粒度要足够小，最好单次编码会话可完成。
3. 每个任务都要有明确的构建或测试命令。
4. 使用状态流转 `pending -> in_progress -> passed`，失败时标记为 `failed`。
5. 如果失败，先把失败原因写入 `claude-progress.txt`，再标记为 `failed`。重试时使用 `failed -> in_progress`。
6. `depends_on` 只填写直接前置任务 ID，禁止引用不存在的任务。
7. `priority` 使用整数，数值越大优先级越高；同优先级按任务 ID 顺序执行。
8. 初始化 `last_error` 为空字符串，`updated_at` 为空字符串；由 `update-progress.ps1` 在流转时自动维护。
9. 当 Qt UI 是前置条件时，先安排 UI 任务，再安排逻辑任务。
10. 任务一旦生成就尽量保持 ID 稳定；新增任务追加，不要重排已通过项。

## 响应中必须包含

- 范围摘要
- 有序任务列表
- 风险或未知项
- 更新的文件

## 收尾检查

结束前确认：

- 每个任务都包含 `id`、`name`、`status`、`depends_on`、`priority`、`test_command`、`last_error`、`updated_at`、`acceptance_criteria`
- 没有任务仍然含糊或不可验证
- 任务顺序可以体现依赖关系
