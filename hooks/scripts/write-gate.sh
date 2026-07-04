#!/bin/bash
# write-gate.sh — PreToolUse 写代码门控
# exit 1 = 阻塞，exit 0 = 放行
# 失败安全：任何解析错误 exit 0（放行）

input=$(cat)

# 解析操作类型
operation=$(echo "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool','') or d.get('name',''))" 2>/dev/null)
[ -z "$operation" ] && exit 0
case "$operation" in Write|Edit) ;; *) exit 0 ;; esac

# 解析文件路径
file_path=$(echo "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path','') or '')" 2>/dev/null)
[ -z "$file_path" ] && exit 0
file_path="${file_path//\\//}"

# 白名单：.claude/ 和 .md 文件放行
case "$file_path" in
    .claude/*) exit 0 ;;
    *.md) exit 0 ;;
esac

# 查找 features.json
dir=$(dirname "$file_path")
features_path=""
while [ -n "$dir" ] && [ -d "$dir" ]; do
    candidate="$dir/.claude/animus/features.json"
    if [ -f "$candidate" ]; then
        features_path="$candidate"
        break
    fi
    parent=$(dirname "$dir")
    [ "$parent" = "$dir" ] && break
    dir="$parent"
done

[ -z "$features_path" ] && exit 0

# 检查 config.toml 是否关闭门控
config_dir=$(dirname "$(dirname "$features_path")")
config_path="$config_dir/config.toml"
if [ -f "$config_path" ]; then
    gate_disabled=$(python3 -c "
import tomllib, sys
try:
    with open('$config_path', 'rb') as f:
        c = tomllib.load(f)
        g = c.get('gates', {})
        print('false' if g.get('require_task_before_write', True) else 'true')
except: print('false')
" 2>/dev/null)
    [ "$gate_disabled" = "true" ] && exit 0
fi

# 检查有无 in_progress 任务
in_progress=$(python3 -c "
import json, sys
try:
    with open('$features_path', 'rb') as f:
        d = json.loads(f.read())
    tasks = d.get('tasks', d.get('initial_tasks', []))
    if isinstance(tasks, dict):
        for t in tasks.values():
            if t.get('status') == 'in_progress':
                print('1'); sys.exit(0)
    else:
        for t in tasks:
            if t.get('status') == 'in_progress':
                print('1'); sys.exit(0)
except: pass
print('0')
" 2>/dev/null)

if [ "$in_progress" = "1" ]; then
    exit 0  # 有任务，放行
fi

# 无任务，阻塞
echo "❌ 阻塞：写代码前需要先有 in_progress 任务" >&2
echo "   请先执行 /animus-dev 完成需求确认和任务拆分" >&2
exit 1
