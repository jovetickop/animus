#!/bin/bash
# Stop 钩子 — 会话结束时检查未完成任务的状态
# 解析 features.json，输出中文警告提醒用户有未完成的任务
# 始终以 exit 0 退出

# 确定项目根目录（从脚本路径 .claude/hooks/scripts/ 向上三级）
script_dir="$(cd "$(dirname "$0")" && pwd)"
project_root="$(cd "$script_dir/../../.." && pwd)"
features_path="$project_root/.claude/state/features.json"

# 检查 features.json 是否存在
[ -f "$features_path" ] || exit 0

# 检查是否安装了 jq（JSON 解析工具）
if ! command -v jq >/dev/null 2>&1; then
    # 无 jq 时无法解析 JSON，静默退出
    exit 0
fi

# 查找所有 status 为 in_progress 的任务
# 兼容数组格式和对象格式（initial_tasks/tasks 字段）
in_progress=$(jq -r '
    if type == "object" then
        .initial_tasks // .tasks // []
    else
        .
    end
    | .[]
    | select(.status == "in_progress")
    | "  - \(.id) : \(.name // "未命名")"
' "$features_path" 2>/dev/null)

if [ -n "$in_progress" ]; then
    echo "===== 任务状态检查 ====="
    echo "以下任务正在进行中，尚未完成："
    echo "$in_progress"
    echo "请确认这些任务是否需要继续或回退状态。"
fi

exit 0
