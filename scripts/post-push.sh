#!/bin/bash
# post-push: 提交推送后自动更新本地插件
# 依赖 claude CLI，安装到 .git/hooks/post-push 或通过 git config core.hooksPath 启用

CONFIG_FILE=".claude/animus/project-config.json"

# 检查开关（用 Python 解析 JSON，避免 grep 误匹配）
if [ -f "$CONFIG_FILE" ]; then
  python -c "
import json, sys
with open('$CONFIG_FILE') as f:
    cfg = json.load(f)
sys.exit(0 if not cfg.get('auto-update-plugin', True) else 1)
" 2>/dev/null && exit 0
fi

echo "=== 更新插件 animus ==="
claude plugin update animus --scope user 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  插件自动更新失败，请手动执行: claude plugin update animus"
    echo "   然后执行: /reload-plugins（在 Claude Code 中）"
else
    echo "✅ 插件已更新，下次 Claude Code 会话生效"
    echo "   或在 Claude Code 中执行 /reload-plugins 立即生效"
fi
