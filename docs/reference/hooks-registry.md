---
type: reference
audience: regular-user
---

# 钩子注册表

> Animus 注册的 Claude Code 运行时钩子及脚本路径。

---

## 注册文件

`hooks/hooks.json` 文件中注册了 4 种钩子，覆盖整个会话生命周期。

## 钩子一览

| 钩子 | 触发时机 | 作用 | 超时 |
|------|---------|------|------|
| PreToolUse | Write/Edit 前 | write-gate 门控 + 备份 features.json + GBK→UTF-8 | 5s + 10s |
| PostToolUse | Write/Edit 后 | clang-format + format-all 多语言格式化 + UTF-8→GBK | 10s + 15s |
| PreCompact | 上下文压缩前 | 刷进度（JSONL compact 事件 + features→task_plan 同步） | 10s |
| Stop | 会话结束时 | 检查未完成任务，输出恢复提示 | 10s |

## 高可用设计

每个钩子同时提供 bash（`.sh`）和 Python（`.py`）两个实现：

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/xxx.sh\" 2>/dev/null || python \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/xxx.py\" 2>/dev/null || exit 0"
}
```

- bash 分支失败 → Python 分支降级
- 两个都失败 → `exit 0` 不阻塞主流程

## 脚本路径

```
hooks/scripts/
├── clang-format.py / .sh    ← C++ 格式化
├── format-all.py             ← 多语言格式化分发
├── encoding-bridge.py        ← GBK↔UTF-8 双向转换
├── pre-tool-use.py / .sh     ← PreToolUse 备份
├── pre-compact.py / .sh      ← PreCompact 同步
├── stop-check.py / .sh       ← Stop 恢复提示
├── write-gate.py / .sh       ← Write 前门控
```
