#!/bin/bash
# PreToolUse 钩子 — Write/Edit 操作前自动备份 features.json 状态文件
# 备份文件名为 features.json.bak.YYYYMMDDHHMMSS，保留最近 5 个备份
# 始终以 exit 0 退出，绝不阻塞操作

input=$(cat)

# 从 stdin JSON 中提取操作类型（tool 或 name 字段）
operation=$(echo "$input" | sed -n 's/.*"tool":"\([^"]*\)".*/\1/p')
if [ -z "$operation" ]; then
    operation=$(echo "$input" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p')
fi

# 仅处理 Write/Edit 操作
case "$operation" in
    Write|Edit) ;;
    *) exit 0 ;;
esac

# 提取被写入的文件路径
file_path=$(echo "$input" | sed -n 's/.*"file_path":"\([^"]*\)".*/\1/p' | head -1)
[ -z "$file_path" ] && exit 0

# 将 Windows 反斜杠路径转换为 Unix 正斜杠
file_path="${file_path//\\//}"

# 从目标文件向上遍历目录，查找 .claude/state/features.json
dir=$(dirname "$file_path")
features_path=""

while [ -n "$dir" ] && [ -d "$dir" ]; do
    candidate="$dir/.claude/state/features.json"
    if [ -f "$candidate" ]; then
        features_path="$candidate"
        break
    fi
    parent=$(dirname "$dir")
    # 到达根目录（/ 或 C: 等），停止遍历
    if [ "$parent" = "$dir" ]; then break; fi
    dir="$parent"
done

# 未找到 features.json，无需备份
[ -z "$features_path" ] && exit 0

# 生成带时间戳的备份文件名：features.json.bak.YYYYMMDDHHMMSS
timestamp=$(date +%Y%m%d%H%M%S)
backup_dir=$(dirname "$features_path")
backup_path="$backup_dir/features.json.bak.$timestamp"

# 执行备份，失败时静默退出
cp "$features_path" "$backup_path" 2>/dev/null || exit 0

# 清理旧备份：只保留最近 5 个（按文件名排序）
ls -1 "$backup_dir"/features.json.bak.* 2>/dev/null | sort -r | tail -n +6 | while read -r old_backup; do
    rm -f "$old_backup"
done

exit 0
