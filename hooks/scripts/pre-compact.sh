#!/bin/bash
# PreCompact 钩子 — 上下文压缩前刷新进度到 claude-progress.txt
# 追加时间戳 [COMPACT] 标记行，并输出 features.json 任务完成摘要
# 始终以 exit 0 退出，不影响压缩流程

# 确定项目根目录（从脚本路径 .claude/hooks/scripts/ 向上三级）
script_dir="$(cd "$(dirname "$0")" && pwd)"
project_root="$(cd "$script_dir/../../.." && pwd)"
# 统一路径查找：features.json 固定在 .claude/harness-cc/
features_path="$project_root/.claude/harness-cc/features.json"

# 旧路径 deprecated 警告（同时检查 .claude/state/ 和 .claude/harness/）
if [ -f "$project_root/.claude/state/features.json" ]; then
    echo "[harness-cc] WARNING: features.json 在旧路径 .claude/state/ (deprecated). 请迁移到 .claude/harness-cc/"
fi
if [ -f "$project_root/.claude/harness/features.json" ]; then
    echo "[harness-cc] WARNING: features.json 在旧路径 .claude/harness/ (deprecated). 请迁移到 .claude/harness-cc/"
fi

progress_path="$project_root/.claude/harness-cc/claude-progress.txt"

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
        # 3) 写入 JSONL compact 事件
        history_path="$project_root/.claude/harness-cc/harness-history.jsonl"
        if [ -f "$history_path" ]; then
            timestamp=$(date "+%Y-%m-%d %H:%M:%S")
            echo "{\"type\":\"compact\",\"timestamp\":\"$timestamp\",\"reason\":\"context_window_reached\",\"summary\":\"$stats\"}" >> "$history_path"
        fi
    fi
fi

exit 0
