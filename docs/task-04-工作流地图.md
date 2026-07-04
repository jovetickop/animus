# 优化任务 ④：工作流地图 / 智能导航

> 对应路线图：Phase 2 — 能力增强
> 解决：用户只能自己判断"下一步做什么"

---

## 一、更改原因

### 1.1 当前问题

- 用户做完一个命令后不知道"下一步做什么"
- 没有上下文感知的"基于当前状态推荐下一步"
- 新用户需要记忆 8 个命令的使用顺序

### 1.2 解决后的效果

- `/animus-status` 输出底部自动推荐下一步
- 推荐基于当前项目状态实时计算
- 新用户不需要记忆命令顺序

---

## 二、更改方案

### 2.1 依赖图

在 `scripts/engine/cmd_status.py` 中内嵌命令依赖图 DAG：

```python
WORKFLOW_GRAPH = {
    "animus-setup": {
        "pre": [],
        "post": [".claude/animus/features.json 存在"],
        "next": ["animus-dev"]
    },
    "animus-dev": {
        "pre": [".claude/animus/features.json 存在"],
        "post": ["features.json 有 in_progress 任务"],
        "next": ["animus-review", "animus-status"]
    },
    "animus-review": {
        "pre": ["features.json 有 passed 任务"],
        "post": ["审查报告已生成"],
        "next": ["animus-archive", "animus-handoff"]
    },
    "animus-archive": {
        "pre": ["所有任务已完成"],
        "post": ["features.json 已清空"],
        "next": ["animus-dev"]
    },
    "animus-handoff": {
        "pre": ["任意状态"],
        "post": ["handoff.json 已生成"],
        "next": ["animus-continue"]
    },
    "animus-continue": {
        "pre": ["handoff.json 存在"],
        "post": ["上下文已恢复"],
        "next": ["animus-dev"]
    },
    "animus-status": {
        "pre": [],
        "post": [],
        "next": []
    },
}
```

### 2.2 推荐逻辑

推荐规则按优先级排序，只推荐最匹配的一条：

| # | 条件 | 推荐命令 | 理由 |
|---|------|---------|------|
| 1 | 无 features.json | `/animus-setup` | 项目还没初始化 |
| 2 | features.json 无任务 | `/animus-dev` | 还没拆需求 |
| 3 | 有 pending 任务 | `/animus-dev` | 有任务等实施 |
| 4 | 有 in_progress 任务 | `/animus-dev` | 继续当前任务 |
| 5 | 有 passed 任务未审查 | `/animus-review` | 代码需要审查 |
| 6 | 审查不通过 | `/animus-dev` | 修复后重审 |
| 7 | 全部 passed | `/animus-archive` 或 `/animus-handoff` | 归档或保存 |

### 2.3 输出格式

`/animus-status` 输出底部追加推荐区块：

```
📋 任务进度：3/8 完成（37%）
   ✅ T001 修按钮颜色 — passed
   ✅ T002 调整间距 — passed
   🔄 T003 加 PDF 导出 — in_progress
   ⏳ T004-T008 — pending

💡 推荐下一步：/animus-dev 继续实施 T003
   或 /animus-review 审查已完成的 T001、T002
```

### 2.4 改动文件

| 文件 | 改动 |
|------|------|
| `scripts/engine/cmd_status.py` | 加 WORKFLOW_GRAPH dict + 推荐逻辑 |
| `commands/animus-status.md` | 输出追加推荐块 |

---

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 无影响——实时计算，200 个任务 < 5ms |
| 兼容性 | 完全向后兼容——仅在原输出底部追加 |
| 降级 | WORKFLOW_GRAPH 缺失任一命令时跳过该命令推荐，不 crash |

## 四、验证方法

1. 未初始化项目 → 推荐 `/animus-setup`
2. features.json 无任务 → 推荐 `/animus-dev`
3. 有 in_progress 任务 → 推荐 `/animus-dev` 继续
4. 有 passed 任务未审查 → 推荐 `/animus-review`
5. 全部 passed → 推荐 `/animus-archive`
