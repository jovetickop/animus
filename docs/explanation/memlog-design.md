---
type: explanation
audience: regular-user
---

# Memlog 事件源设计

> Memlog 是 Animus 的单一事件源——所有状态变更、决策、辩论都追加记录到 memlog 目录，
> features.json 等状态文件由 memlog 派生。

---

## 目录结构

```
.claude/animus/memlog/
├── 2026-07-04-10-01-23-创建任务-T003-添加PDF导出功能.md
├── 2026-07-04-10-30-45-状态变更-T003-进行中.md
├── 2026-07-04-11-00-12-决策-选择QProcess作为后端.md
├── 2026-07-04-11-30-00-归档-迭代003.md
├── 2026-07-04-14-00-00-辩论-架构评审-T003.md
└── ...
```

文件名格式：`YYYY-MM-DD-HHmm-{事件类型}-{描述}.md`

## 事件类型

| 类型 | 说明 | 写入时机 |
|------|------|---------|
| 创建任务 | 任务创建时写入 | `animus-engine.py` 创建任务后 |
| 状态变更 | 状态流转时写入 | `transition` 命令执行后 |
| 决策 | 技术/架构决策时写入 | 开发者或 AI 记录 |
| 交接 | 记录交接时刻 | 跨会话恢复时 |
| 归档 | 归档迭代时写入 | `archive` 命令执行时 |
| 辩论 | Party Mode 辩论全量日志 | 辩论结束后 |

## 核心原则

### Append-only

当前迭代中 memlog **只追加不修改**。归档时整份复制到 `archive/iter-xxx/memlog/` 后清空原目录。

### 单一事件源

`features.json` 由 memlog 派生，可删除后重建：

```bash
python animus-engine.py rebuild
```

这意味着 memlog 是真相来源，`features.json` 只是快照。

### 灾难恢复

memlog 文件是普通 Markdown——即使引擎 CLI 不可用，也可以直接读文件恢复上下文。
