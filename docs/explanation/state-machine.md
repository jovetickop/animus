---
type: explanation
audience: regular-user
---

# 状态机设计

> Animus 任务状态机的流转规则和约束。

---

## 状态流转

```
pending → in_progress → passed → completed
                    ↘ failed → in_progress/pending
```

| 流转 | 条件 |
|------|------|
| `pending → in_progress` | 前置依赖全部 passed（如果有） |
| `in_progress → passed` | 通过 Oracle 验证门控（verify_command） |
| `in_progress → failed` | 必须提供失败原因 |
| `failed → in_progress` | 重试 |
| `passed → completed` | 所有任务已完成 |
| `completed` | 终态（可重入 in_progress） |

## 硬约束

- **同时只能有一个** `in_progress` 任务
- `depends_on` 构建 DAG，只能依赖**直接前置**任务
- **非法流转 `exit 1`**——此契约不应放宽
- `in_progress → passed` 必须有构建/测试证据

## CLI 使用

```bash
python animus-engine.py transition T001 in_progress
python animus-engine.py transition T001 passed --evidence "test all pass"
python animus-engine.py transition T001 failed
```
