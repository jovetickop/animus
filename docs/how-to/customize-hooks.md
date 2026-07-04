---
type: how-to
audience: plugin-developer
---

# 如何编写自定义 Hook

> 在 Claude Code 会话生命周期中注册自定义自动化脚本。

---

## Hook 类型

| 钩子 | 触发时机 | 适用场景 |
|------|---------|---------|
| PreToolUse | Write/Edit 前 | 门控检查、备份、编码转换 |
| PostToolUse | Write/Edit 后 | 格式化、校验、同步 |
| PreCompact | 上下文压缩前 | 刷进度、事件写入 |
| Stop | 会话结束时 | 清理、恢复提示 |

## 步骤

### 1. 创建脚本

在 `hooks/scripts/` 下新建脚本，建议同时提供 Python 和 Shell 版本：

```
hooks/scripts/my-custom-hook.py
hooks/scripts/my-custom-hook.sh
```

### 2. 注册到 hooks.json

在 `hooks/hooks.json` 中添加：

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/my-custom-hook.sh\" 2>/dev/null || python \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/my-custom-hook.py\" 2>/dev/null || exit 0",
      "timeout": 10
    }
  ]
}
```

### 3. 降级原则

- 脚本失败时 `exit 0`（不阻塞 Claude Code）
- 提供 bash + Python 双实现互为降级
- 设置合理的超时时间（建议 5-15s）
