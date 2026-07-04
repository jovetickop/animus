# 优化任务 ②：Memlog 单一事件源持久化

> 对应路线图：Phase 1 — 快速见效 / P0

---

## 一、更改原因

### 1.1 当前问题

Animus 当前状态数据分散在 4 个文件中：

```
.claude/animus/
├── features.json      # 任务状态（可被直接修改 → 可能损坏）
├── animus-history.jsonl  # 日志（追加但不用于重建）
├── task_plan.md      # 任务计划（与 features.json 可能不一致）
└── handoff.json      # 会话快照（独立保存，不与前三个关联）
```

具体风险：

- **不同步：** features.json 和 task_plan.md 可能因 hook 写一半失败而不一致
- **难恢复：** features.json 损坏或误删后，无法重建任务状态
- **决策丢失：** handoff 只记录当前上下文，不接受"为什么这么做"
- **难追溯：** archive 打包后旧决策无法搜索，只能解包翻 ZIP

### 1.2 解决后的效果

- 任何状态文件损坏 → 跑 `rebuild-from-memlog.py`，10ms 恢复
- 不一致不可能发生：features.json 是派生品，memlog 才是源
- 所有决策永久可查：memlog 永不删除，全文可搜索
- archive 只归档派生文件，memlog 保留在线

---

## 二、更改方案

### 2.1 核心概念

**单一事件源原则：** memlog 是唯一写入入口。features.json、handoff 上下文等全部从 memlog 派生。

```
                    ┌──────────────────┐
                    │     memlog/      │  ← 唯一写入入口
                    │  (append-only)   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              
        features.json    task_plan.md
        (派生重建)       (派生重建)      
```

### 2.2 文件结构

```
.claude/animus/memlog/
├── 2026-07-04-1001-创建任务-T003-添加PDF导出功能.md
├── 2026-07-04-1030-状态变更-T003-进行中.md
├── 2026-07-04-1100-决策-选择QProcess作为后端.md
├── 2026-07-04-1130-交接-迭代2.md
└── ...
```

每个事件一个文件，文件名格式：

```
YYYY-MM-DD-HHmm-{事件类型}-{可选上下文}.md
```

所有文件名和内容使用中文。

### 2.3 事件类型定义

| 事件类型 | 文件名示例 | 触发点 | 内容字段 |
|---------|-----------|--------|---------|
| `创建任务` | `2026-07-04-1001-创建任务-T003-标题.md` | 任务创建 | task_id, title, spec |
| `状态变更` | `2026-07-04-1030-状态变更-T003-进行中.md` | 状态流转 | task_id, from, to, evidence |
| `决策` | `2026-07-04-1100-决策-选择QProcess作为后端.md` | 技术/架构决策 | context, options, decision, rationale |
| `交接` | `2026-07-04-1130-交接-迭代2.md` | traceability（记录交接时刻） | task_id, progress, next_steps, risks |
| `归档` | `2026-07-04-1200-归档-迭代003.md` | `/animus-archive` | iteration, scope, summary |
| `辩论` | `2026-07-04-1400-辩论-架构评审-T003.md` | Party Mode | template, participants, consensus, disagreements |

### 2.4 事件文件格式

每个事件是一个标准 markdown 文件，YAML frontmatter 描述元数据，正文写详情：

```markdown
---
type: create-task
timestamp: 2026-07-04T10:01:00+08:00
task_id: T003
---

# 创建任务：添加 PDF 导出功能

## Spec

**Why：** 客户需要在离线状态下分享报告

**Capabilities：**
- 选择导出范围
- 生成 PDF
- 选择保存路径

**Constraints：**
- 依赖 Qt PDF 模块
- 导出时间不超过 5 秒

**Non-goals：**
- 不处理加密 PDF
- 不支持批量导出

**Success：** 用户选定 3 页报告后 3 秒内生成可打开的 PDF
```

```markdown
---
type: decision
timestamp: 2026-07-04T11:00:00+08:00
task_id: T003
---

# 决策：选择 QProcess 作为后端进程管理器

**Context：** T003 涉及 PDF 生成，需要在主进程外启动 wkhtmltopdf

**Options considered：**
1. QProcess（Qt 内置）
2. QThread + 直接调用
3. 独立 Python worker

**Decision：** QProcess

**Rationale：**
- Qt 内置，零依赖
- 与主进程隔离，崩溃不影响 UI
- 信号槽回调天然适配事件驱动
```

### 2.5 改动清单

#### 2.5.1 新建 `scripts/rebuild-from-memlog.py`

功能：扫描 memlog 目录，按时间排序事件，重建 features.json

伪逻辑：

```python
def rebuild():
    events = sorted(glob("memlog/*.md"))
    features = {"tasks": {}, "progress": {}}

    for event in events:
        match event.type:
            case "create-task":
                features["tasks"][event.task_id] = {
                    "title": ..., "spec": ..., "status": "pending"
                }
            case "status-change":
                features["tasks"][event.task_id]["status"] = event.to
            case "archive":
                features["metadata"]["archived_iterations"].append(event.iteration)

    write_features_json(features)
```

性能预期：200 个事件扫描 ≈ 20ms

#### 2.5.2 新建 `scripts/migrate-to-memlog.py`

功能：一次性迁移脚本，读当前 features.json，为每个已存在的任务写 `create-task` 事件

```python
def migrate(features_path):
    features = load_json(features_path)
    for tid, task in features.get("tasks", {}).items():
        write_event("create-task", task_id=tid, spec=task.get("spec"))
        if task["status"] in ["passed", "failed", "in_progress"]:
            write_event("status-change", task_id=tid,
                        from_="pending", to=task["status"])
```

执行一次后不再需要。

#### 2.5.3 修改 `scripts/update-progress.py`

当前功能：更新 features.json 状态。
修改后：先追加 memlog 事件，再触发 rebuild-from-memlog。

```python
def update_task_status(task_id, to, evidence=None):
    # 1. 写 memlog
    write_event("status-change", task_id=task_id, to=to, evidence=evidence)
    # 2. 重建 features.json
    rebuild_from_memlog()
```

#### 2.5.4 修改 `hooks/scripts/pre-compact.py` 和 `.sh`

当前：同时写 features.json + JSONL + task_plan.md
修改后：只追加 memlog 事件，删除多文件同步逻辑

#### 2.5.5 `/animus-handoff` 和 `/animus-continue` — 已移除

handoff/continue 作为独立命令已移除，功能由 memlog + `/animus-dev` 自动接管：
- 任务状态 → memlog 事件自动记录，无需手动 handoff
- 上下文恢复 → `/animus-dev` 启动时自动检测 memlog → 重建 features.json
- memlog 的 `交接` 事件类型保留用于 traceability
- `engine/` 中移除 `cmd_handoff.py` 和 `cmd_continue.py` 子命令

恢复入口统一为：`/animus-dev`（自动检测旧进度）

#### 2.5.6 修改 `commands/animus-archive.md`

当前：打包 features.json + JSONL + task_plan.md
修改后：**memlog 不归档**，只归档派生文件。archive 事件写入 memlog 记录"何时归档了什么"

### 2.6 不改动的部分

- features.json schema 本身 — 只改写入路径，不改字段结构
- JSONL 日志 — 保留作为调试日志，但不再作为状态源
- 现有 archive 格式 — 不变，只加 archive 事件

### 2.7 改动文件清单

```
新建 scripts/rebuild-from-memlog.py     # 核心重建引擎
新建 scripts/migrate-to-memlog.py       # 迁移脚本
修改 scripts/update-progress.py         # 写入改为 memlog + 重建
修改 hooks/scripts/pre-compact.py      # 同步逻辑简化
修改 hooks/scripts/pre-compact.sh       # 同步逻辑简化
删除 commands/animus-handoff.md          # 已移除，memlog 自动接管
删除 commands/animus-continue.md        # 已移除，/animus-dev 自动恢复
修改 commands/animus-archive.md          # archive 记录事件
```

共 **6 个文件**（2 新建 + 4 修改）。

---

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 200 事件重建 ≈ 20ms；文件数 1000+ 时 `ls` 可能变慢（可接受范围） |
| 兼容性 | 旧 handoff.json 格式不兼容——迁移脚本一次性转换后不再需要 |
| 降级 | 重建失败时保留最近一次 features.json 副本（`.claude/animus/features.json.bak`）作为兜底 |

## 四、验证方法

1. **重建测试：** 执行迁移脚本后，手动删掉 features.json，跑 `rebuild-from-memlog.py`，验证 features.json 内容与删除前一致
2. **一致性测试：** 执行一系列任务状态变更，检查每次 rebuild 后 features.json 是否反映最新状态
3. **自动恢复测试：** 清空 features.json（memlog 保留），执行 `/animus-dev` → 确认自动检测 memlog 并恢复进度
4. **archive 测试：** 执行 `/animus-archive` → 确认 memlog 有 archive 事件 → 确认派生文件已打包但 memlog 未归档
