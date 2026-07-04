# 优化任务 ⑥：多 IDE 引擎抽离

> 对应路线图：Phase 2 — 能力增强
> 解决：核心逻辑锁在 Claude Code 运行时，无法移植到其他 IDE

---

## 一、更改原因

### 1.1 当前问题

- 状态机逻辑分散在 PowerShell 脚本（`.ps1`）和 Python 脚本中
- 所有 hooks 是 Claude Code 运行时钩子，强绑定
- `.md` 命令依赖 Claude Code agent 机制解析
- 无法移植到 Cursor、Windsurf 等其他 IDE

### 1.2 解决后的效果

- 核心引擎抽离为独立 Python CLI：`python animus-engine.py <子命令>`
- 当前只做 Claude Code adapter，输出格式不变
- 未来其他 IDE 只需写 adapter 调 engine CLI

---

## 二、更改方案

### 2.1 目录结构

```
scripts/
├── animus-engine.py              # 入口：argparse 分发子命令
└── engine/
    ├── __init__.py
    ├── cmd_status.py             # /animus-status 逻辑
    ├── cmd_transition.py         # 状态流转
    ├── cmd_validate.py           # features.json 校验（含 4 条法则）
    ├── cmd_archive.py            # 归档执行 + 迭代总结报告
    # cmd_handoff.py / cmd_continue.py 已移除（由 memlog 自动接管）
    └── cmd_rebuild.py            # 从 memlog 重建 features.json
```

### 2.2 入口设计

```python
# animus-engine.py
import argparse

def main():
    parser = argparse.ArgumentParser(prog="animus-engine")
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p = sub.add_parser("status", help="显示任务状态")

    # transition
    p = sub.add_parser("transition", help="状态流转")
    p.add_argument("task_id")
    p.add_argument("to", choices=["pending", "in_progress", "passed", "failed"])

    # validate
    p = sub.add_parser("validate", help="校验 features.json")

    # archive
    p = sub.add_parser("archive", help="执行归档")
    p.add_argument("--name", default="")
    p.add_argument("--discard", action="store_true")

    # handoff / continue 已移除 — 由 memlog + /animus-dev 自动接管

    # rebuild
    p = sub.add_parser("rebuild", help="从 memlog 重建 features.json")

    args = parser.parse_args()

    # dispatch
    if args.command == "status":
        from engine.cmd_status import run; run()
    elif args.command == "transition":
        from engine.cmd_transition import run; run(args.task_id, args.to)
    # ...

if __name__ == "__main__":
    main()
```

### 2.3 与现有命令的衔接

现有 `.md` 命令中，agent 原来手写 JSON 或调脚本的地方改为调 engine CLI：

| 命令 | 原始做法 | 改为 |
|------|---------|------|
| `/animus-status` | agent 读 features.json 输出 | `python animus-engine.py status` |
# `/animus-handoff` 和 `/animus-continue` 已移除 — memlog 自动接管
| `/animus-archive` | agent 打包+清空 | `python animus-engine.py archive --name "xxx"` |

hooks 中的脚本同理，改为调 engine CLI。

### 2.4 改动文件

| 文件 | 改动 |
|------|------|
| 新建 `scripts/animus-engine.py` | 入口路由 |
| 新建 `scripts/engine/__init__.py` | 包初始化 |
| 新建 `scripts/engine/cmd_status.py` | 状态子命令 |
| 新建 `scripts/engine/cmd_transition.py` | 流转子命令 |
| 新建 `scripts/engine/cmd_validate.py` | 校验子命令 |
| 新建 `scripts/engine/cmd_archive.py` | 归档子命令 + 迭代总结报告 |
| 新建 `scripts/engine/cmd_rebuild.py` | 重建子命令 |
| 修改 `commands/animus-archive.md` | 调 engine CLI |
| 删除 `commands/animus-handoff.md` | 已移除，memlog 自动接管 |
| 删除 `commands/animus-continue.md` | 已移除，/animus-dev 自动恢复 |
| 修改 hooks 脚本 | 调 engine CLI |

---

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | engine CLI 启动延迟约 50ms，相较纯脚本可忽略 |
| 兼容性 | 输出格式不变，命令接口不变，用户无感知 |
| 降级 | 子命令独立运行，单个失败不影响其他 |
| 风险 | PowerShell 写的状态机逻辑需完整翻译到 Python，不能漏分支 |

## 四、验证方法

1. 执行 `python animus-engine.py status` → 确认输出与 `/animus-status` 一致
2. 执行 `python animus-engine.py transition T001 in_progress` → 确认 features.json 状态变更
3. 执行 `python animus-engine.py rebuild` → 确认从 memlog 重建成功
4. 确认 `/animus-handoff` 和 `/animus-continue` 不再可用
5. 确认 `/animus-dev` 在 memlog 存在时自动输出「检测到上次进度」
