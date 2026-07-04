# ~~Handoff/Continue/Archive 脚本化~~（已取消）

> **状态：已取消** — handoff/continue 作为独立命令已移除
> 功能由 memlog + `/animus-dev` 自动接管，不再需要脚本化
> 仅 archive 脚本化保留（归入 `engine/cmd_archive.py`）
> 所属任务：⑥ 多 IDE 引擎抽离

---

## 一、更改原因

### 1.1 当前问题

三个命令当前都是 .md 文件，依赖 agent 做结构化操作：

| 命令 | 当前实现 | 问题 |
|------|---------|------|
| `/animus-handoff` | agent 读多个文件 → 组装 JSON → 写 handoff.json | JSON 格式错乱、字段遗漏 |
| `/animus-continue` | agent 读 handoff.json → 解析 → 输出恢复报告 | 解析 JSON 时可能出错 |
| `/animus-archive` | agent 问用户问题 → 调 archive-iteration.py | 交互部分 agent 做，脚本做执行 |

关键是：**这些操作不需要 LLM 推理**，纯结构化数据操作，脚本更快更准。

### 1.2 解决后的效果

- handoff：脚本自动收集状态文件，序列化为 JSON。agent 只负责补充推理上下文。
- continue：脚本自动读取 handoff.json，重建上下文摘要。agent 只负责解读输出。
- archive：脚本自动完成打包+清空+编号。agent 只负责命名确认。

---

## 二、更改方案

### 2.1 总体设计

每个命令拆为两层，统一由 `animus-engine.py` 调度：

```
┌──────────────────┐
│  .md 命令入口     │  ← 保留，负责 LLM 推理部分
│  (agent layer)   │
└──────┬───────────┘
       │ python animus-engine.py <子命令>
┌──────▼───────────┐
│  scripts/animus- │  ← engine 统一入口
│  engine.py       │
│  └── engine/     │
│      ├── cmd_handoff.py   │
│      ├── cmd_continue.py  │
│      └── cmd_archive.py   │
└──────────────────┘
```

agent 不再直接 write JSON、parse JSON、copy dirs。这些交给 engine 子命令。

### 2.2 `/animus-handoff` 脚本化

#### 当前问题

agent 自己组装 handoff.json，容易：
- 忘记读某些状态文件
- JSON 格式错误（多余逗号、引号不闭合）
- 字段遗漏（如 session_id、created_at）

#### 改后流程

```
/animus-handoff
  → 步骤 1：调 python animus-engine.py handoff-serialize
     脚本自动：
       - 读 features.json（任务状态）
       - 读 task_plan.md（如果存在）
       - 读 findings.md（如果存在）
       - 读 feature-detail.md（如果存在）
       - 生成 session_id（8 字符 hex）
       - 写 .claude/animus/handoff.json（包含所有状态 + 元数据）
     输出："handoff.json 已生成，共 N 个任务，当前任务：Txxx"
  → 步骤 2：agent 输出当前推理上下文、决策、下一步计划
     （agent 负责 LLM 能做的事：总结、推理、预测）
  → 步骤 3：agent 调 python animus-engine.py handoff-update --context "推理摘要"
     脚本将 agent 的输出追加到 handoff.json 的 context 字段
```

#### 新建脚本 `scripts/handoff-serialize.py`

```python
#!/usr/bin/env python
"""
序列化当前 animus 状态到 handoff.json。
只依赖标准库，不引入额外包。
"""

import json
import os
import hashlib
import time
from datetime import datetime, timezone

ANIMUS_DIR = ".claude/animus"
FILES_TO_READ = [
    "features.json",
    "task_plan.md",
    "findings.md",
    "feature-detail.md",
]


def generate_session_id():
    """生成 8 字符 hex 的 session_id"""
    raw = f"{time.time()}{os.urandom(8)}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def find_current_task(features):
    """找 status=in_progress 的任务"""
    tasks = features.get("tasks", {})
    for tid, task in tasks.items():
        if task.get("status") == "in_progress":
            return {"id": tid, "title": task.get("title")}
    return None


def serialize():
    animus_dir = ANIMUS_DIR
    if not os.path.isdir(animus_dir):
        print("未找到 .claude/animus 目录，需要先执行 /animus-setup")
        return False

    # 读状态文件
    state = {}
    for name in FILES_TO_READ:
        path = os.path.join(animus_dir, name)
        if name.endswith(".json"):
            state[name] = load_json(path)
        else:
            state[name] = load_text(path)

    # 找当前任务
    features = state.get("features.json")
    current_task = find_current_task(features) if features else None

    # 状态统计
    task_count = 0
    if features and "tasks" in features:
        task_count = len(features["tasks"])

    # 构建 handoff
    handoff = {
        "session_id": generate_session_id(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "saved",
        "current_task": current_task,
        "task_count": task_count,
        "state_snapshot": state,
        "context": {
            "recent_thinking": [],
            "decisions": [],
            "pending_issues": [],
            "key_files_read": [],
            "next_intended": "",
        },
    }

    handoff_path = os.path.join(animus_dir, "handoff.json")
    with open(handoff_path, "w", encoding="utf-8") as f:
        json.dump(handoff, f, ensure_ascii=False, indent=2)

    task_info = f"当前任务：{current_task['title']}" if current_task else "无进行中任务"
    print(f"handoff.json 已生成，共 {task_count} 个任务，{task_info}")
    return True


if __name__ == "__main__":
    serialize()
```

#### 新建脚本 `scripts/handoff-update.py`

```python
#!/usr/bin/env python
"""
将 agent 提供的上下文信息追加到 handoff.json。
"""

import json
import sys
import os

ANIMUS_DIR = ".claude/animus"

def update_context(context_text):
    handoff_path = os.path.join(ANIMUS_DIR, "handoff.json")
    if not os.path.exists(handoff_path):
        print("handoff.json 不存在")
        return False

    with open(handoff_path, "r", encoding="utf-8") as f:
        handoff = json.load(f)

    handoff["context"]["recent_thinking"].append(context_text)
    handoff["context"]["pending_issues"] = handoff["context"].get("pending_issues", [])

    with open(handoff_path, "w", encoding="utf-8") as f:
        json.dump(handoff, f, ensure_ascii=False, indent=2)

    return True

if __name__ == "__main__":
    context = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read().strip()
    if context:
        update_context(context)
        print("上下文已追加到 handoff.json")
```

### 2.3 `/animus-continue` 脚本化

#### 当前问题

agent 读 handoff.json 后要自己解析 JSON 并输出恢复报告，JSON 解析错误导致恢复失败。

#### 改后流程

```
/animus-continue
  → 步骤 1：调 python animus-engine.py continue-restore
     脚本：
       - 读 handoff.json
       - 生成结构化恢复报告（markdown）
       - 将 handoff.json status 改为 "loaded"
       - 写 .claude/animus/continue-report.md
     输出："continue-report.md 已生成"
  → 步骤 2：agent 读 continue-report.md
     步骤 3：agent 结合当前 features.json 给出下一步建议
```

#### 新建脚本 `scripts/continue-restore.py`

```python
#!/usr/bin/env python
"""
从 handoff.json 恢复上下文，生成恢复报告。
"""

import json
import os
from datetime import datetime, timezone

ANIMUS_DIR = ".claude/animus"


def restore():
    handoff_path = os.path.join(ANIMUS_DIR, "handoff.json")
    if not os.path.exists(handoff_path):
        print("未找到 handoff.json，请先执行 /animus-handoff")
        return False

    with open(handoff_path, "r", encoding="utf-8") as f:
        handoff = json.load(f)

    status = handoff.get("status")
    if status == "loaded":
        print("Handoff 已加载过，当前进度已恢复")
        return True
    if status != "saved":
        print(f"警告：handoff.json 状态异常 ({status})，仍尝试恢复")

    # 读取状态文件
    state = handoff.get("state_snapshot", {})
    features = state.get("features.json")
    tasks = features.get("tasks", {}) if features else {}
    task_count = len(tasks)
    passed = sum(1 for t in tasks.values() if t.get("status") == "passed")
    failed = sum(1 for t in tasks.values() if t.get("status") == "failed")
    pending = sum(1 for t in tasks.values() if t.get("status") == "pending")
    in_progress = sum(1 for t in tasks.values() if t.get("status") == "in_progress")

    current_task = handoff.get("current_task", {})
    context = handoff.get("context", {})
    thinking = context.get("recent_thinking", [])
    pending_issues = context.get("pending_issues", [])
    next_intended = context.get("next_intended", "")

    # 生成恢复报告
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report = f"""# 会话恢复报告

**恢复时间：** {now}
**原会话 ID：** {handoff.get("session_id")}

## 任务统计

- 总任务数：{task_count}
- ✅ 通过：{passed}
- ❌ 失败：{failed}
- ⏳ 待处理：{pending}
- 🔄 进行中：{in_progress}

## 当前任务

"""
    if current_task:
        report += f"- **{current_task.get('id')}**: {current_task.get('title')}\n"
    else:
        report += "无进行中任务\n"

    report += f"""
## 上下文

### 最近思考
"""
    for t in thinking[-3:]:  # 最近 3 条
        report += f"- {t}\n"

    if pending_issues:
        report += "\n### 待处理问题\n"
        for issue in pending_issues:
            report += f"- {issue}\n"

    if next_intended:
        report += f"\n### 下一步计划\n{next_intended}\n"

    report_path = os.path.join(ANIMUS_DIR, "continue-report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # 标记已加载
    handoff["status"] = "loaded"
    with open(handoff_path, "w", encoding="utf-8") as f:
        json.dump(handoff, f, ensure_ascii=False, indent=2)

    print(f"continue-report.md 已生成")
    return True


if __name__ == "__main__":
    restore()
```

### 2.4 `/animus-archive` 脚本化

#### 当前问题

agent 做：
1. 问用户迭代名称
2. 检查未完成任务
3. 问是否丢弃
4. 调 archive-iteration.py
5. 清空 features.json

步骤 1-3 是纯交互，agent 做合适。步骤 4-5 是机械操作，该脚本做。

#### 改后流程

```
/animus-archive
  → 步骤 1：调 python animus-engine.py archive-check
     脚本检查未完成任务，输出统计
  → 步骤 2：agent 用 AskUserQuestion 问用户：
     - 迭代名称
     - 有未完成任务时是否丢弃
  → 步骤 3：调 python animus-engine.py archive --name "<名称>" [--discard]
     脚本：
       - 执行归档（打包 + 压缩）
       - 清空 features.json
       - 写迭代编号
       - 向 memlog 追加 archive 事件
```

#### 新建脚本 `scripts/archive-execute.py`

```python
#!/usr/bin/env python
"""
执行归档操作：打包、清空、写 memlog。
"""

import json
import os
import shutil
import sys
import argparse
from datetime import datetime, timezone

ANIMUS_DIR = ".claude/animus"
ARCHIVE_DIR = os.path.join(ANIMUS_DIR, "archive")
FILES_TO_ARCHIVE = [
    "features.json",
    "handoff.json",
    "continue-report.md",
    "plan-context.md",
    "task_plan.md",
    "findings.md",
    "feature-detail.md",
]


def get_next_iteration():
    """获取下一次迭代编号"""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    existing = [d for d in os.listdir(ARCHIVE_DIR) if d.startswith("iter-")]
    numbers = [int(d.split("-")[1]) for d in existing if d.split("-")[1].isdigit()]
    return max(numbers) + 1 if numbers else 1


def write_archive_event(iteration, name, summary):
    """向 memlog 追加 archive 事件"""
    memlog_dir = os.path.join(ANIMUS_DIR, "memlog")
    os.makedirs(memlog_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    event_path = os.path.join(memlog_dir, f"{timestamp}-archive-iter-{iteration:03d}.md")

    event = f"""---
type: archive
timestamp: {datetime.now(timezone.utc).isoformat()}
iteration: {iteration}
name: {name}
---

# 归档迭代 {iteration}: {name}

## 总结
"""
    if summary:
        event += summary + "\n"
    else:
        event += "无总结\n"

    with open(event_path, "w", encoding="utf-8") as f:
        f.write(event)


def archive(iteration_name, discard=False):
    if not iteration_name:
        iteration_name = f"迭代 {get_next_iteration()}"

    iteration = get_next_iteration()
    iter_dir = os.path.join(ARCHIVE_DIR, f"iter-{iteration:03d}-{iteration_name}")
    os.makedirs(iter_dir, exist_ok=True)

    # 归档文件
    archived = []
    for filename in FILES_TO_ARCHIVE:
        src = os.path.join(ANIMUS_DIR, filename)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(iter_dir, filename))
            archived.append(filename)

    # 清空 features.json
    features_path = os.path.join(ANIMUS_DIR, "features.json")
    empty_features = {"metadata": {}, "tasks": {}}
    with open(features_path, "w", encoding="utf-8") as f:
        json.dump(empty_features, f, ensure_ascii=False, indent=2)

    # 写 memlog
    write_archive_event(iteration, iteration_name, f"归档了 {len(archived)} 个文件")

    print(
        f"归档完成：{iter_dir}\n"
        f"迭代编号：{iteration}\n"
        f"已归档文件：{', '.join(archived)}\n"
        f"features.json 已清空"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="")
    parser.add_argument("--discard", action="store_true")
    args = parser.parse_args()
    archive(args.name, args.discard)
```

### 2.5 改动文件

| 文件 | 改动 |
|------|------|
| 新建 `scripts/engine/cmd_handoff.py` | handoff 序列化（engine 子命令） |
| 新建 `scripts/engine/cmd_continue.py` | continue 恢复（engine 子命令） |
| 新建 `scripts/engine/cmd_archive.py` | 归档执行（engine 子命令） |
| 修改 `scripts/animus-engine.py` | 注册 handoff/continue/archive 子命令路由 |
| 修改 `commands/animus-handoff.md` | 调 `animus-engine.py handoff` 替代手写 JSON |
| 修改 `commands/animus-continue.md` | 调 `animus-engine.py continue` 替代手读 JSON |
| 修改 `commands/animus-archive.md` | 调 `animus-engine.py archive` 执行归档 |

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 引擎启动延迟约 50ms，相较之前纯 .md 执行更稳定 |
| 兼容性 | handoff.json 格式兼容旧版——engine 可读写旧格式 |
| 降级 | engine 子命令独立运行，单个失败不影响其他命令 |
| 与 task-06 关系 | 3 个子命令统一归入 `scripts/engine/*.py`，由 `animus-engine.py` 路由 |

## 四、验证方法

### handoff
1. 有 in_progress 任务时执行 `/animus-handoff` → 确认 handoff.json 包含当前任务
2. 无任务时执行 → 确认 handoff.json 的 current_task 为 null
3. 确认 handoff.json JSON 格式正确
4. 确认 agent 上下文能通过 handoff-update.py 追加

### continue
1. 执行 handoff 后执行 `/animus-continue` → 确认 continue-report.md 生成
2. 确认报告内容与 handoff 时状态一致
3. 重复执行 continue → 显示"已加载过"
4. 无 handoff.json 时执行 → 显示提示

### archive
1. 执行 `/animus-archive` → 确认 archive/iter-xxx 目录创建
2. 确认 features.json 已清空
3. 确认 memlog 有 archive 事件
4. 确认不丢文件（源 features.json 复制到归档目录）
