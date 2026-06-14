#!/bin/bash
# PreCompact 钩子 — 上下文压缩前刷新进度到 claude-progress.txt
# 追加时间戳 [COMPACT] 标记行，并输出 features.json 任务完成摘要
# 始终以 exit 0 退出，不影响压缩流程

# 确定项目根目录（从脚本路径 .claude/hooks/scripts/ 向上三级）
script_dir="$(cd "$(dirname "$0")" && pwd)"
project_root="$(cd "$script_dir/../../.." && pwd)"
# 同时支持 .claude/harness/（init-project.ps1 复制位置）和 .claude/state/（约定位置）
features_path=""
for sub in harness state; do
    candidate="$project_root/.claude/$sub/features.json"
    if [ -f "$candidate" ]; then
        features_path="$candidate"
        break
    fi
done
progress_path="$project_root/.claude/state/claude-progress.txt"
if [ ! -f "$progress_path" ]; then
    progress_path="$project_root/.claude/harness/claude-progress.txt"
fi

# 1) 如果 claude-progress.txt 存在，追加时间戳 [COMPACT] 标记行
if [ -f "$progress_path" ]; then
    timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[COMPACT] 上下文压缩于 $timestamp" >> "$progress_path"
fi

# 2) 如果 features.json 存在，统计任务完成情况并输出摘要
if [ -f "$features_path" ] && command -v jq >/dev/null 2>&1; then
    # 获取总任务数和已完成（passed/completed）任务数
    # 兼容数组格式和对象格式（initial_tasks/tasks 字段）
    stats=$(jq -r '
        if type == "object" then
            .initial_tasks // .tasks // []
        else
            .
        end
        | length as $total
        | (map(select(.status == "passed" or .status == "completed")) | length) as $done
        | "\($done)/\($total)"
    ' "$features_path" 2>/dev/null)

    if [ -n "$stats" ]; then
        echo "[harness-cc] PreCompact: $stats 任务完成"
    fi
fi

exit 0
