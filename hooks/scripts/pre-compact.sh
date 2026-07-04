#!/bin/bash
# PreCompact 钩子 — 上下文压缩前刷新进度到 task_plan.md
# 追加时间戳 [COMPACT] 标记行，并输出 features.json 任务完成摘要
# 始终以 exit 0 退出，不影响压缩流程

# 确定项目根目录（从脚本路径 .claude/hooks/scripts/ 向上三级）
script_dir="$(cd "$(dirname "$0")" && pwd)"
project_root="$(cd "$script_dir/../../.." && pwd)"
# 统一路径查找：features.json 固定在 .claude/animus/
features_path="$project_root/.claude/animus/features.json"

# 旧路径 deprecated 警告（同时检查 .claude/state/ 和 .claude/harness/）
if [ -f "$project_root/.claude/state/features.json" ]; then
    echo "[animus] WARNING: features.json 在旧路径 .claude/state/ (deprecated). 请迁移到 .claude/animus/"
fi
if [ -f "$project_root/.claude/harness/features.json" ]; then
    echo "[animus] WARNING: features.json 在旧路径 .claude/harness/ (deprecated). 请迁移到 .claude/animus/"
fi

history_path="$project_root/.claude/animus/animus-history.jsonl"

# 1) 如果 features.json 存在，统计任务完成情况并输出摘要
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
        echo "[animus] PreCompact: $stats 任务完成"
        # 3) 写入 JSONL compact 事件
        if [ -f "$history_path" ]; then
            timestamp=$(date "+%Y-%m-%dT%H:%M:%S")
            echo "---" >> "$history_path"
            echo "{\"type\":\"compact\",\"timestamp\":\"$timestamp\",\"reason\":\"context_window_reached\",\"summary\":\"$stats\"}" >> "$history_path"
        fi
    fi
fi

# 4) 自动同步 features.json → task_plan.md
task_plan_path="$project_root/.claude/animus/task_plan.md"
if [ -f "$task_plan_path" ]; then
    modified=false
    # 通过 python 解析 JSON 获取已完成任务 id（兼容 initial_tasks/tasks）
    for task in $(python -c "
import json, sys
with open('$features_path', 'r') as f:
    data = json.load(f)
tasks = data.get('initial_tasks', data.get('tasks', []))
for t in tasks:
    if t.get('status') in ('passed', 'completed'):
        print(t['id'])
" 2>/dev/null); do
        # 在当前 task_plan 中查找 [ ] Txxx 并替换为 [x]
        if grep -q "\[ \].*${task}" "$task_plan_path" 2>/dev/null; then
            if sed -i "s/\[ \]\(.*${task}\)/[x]\1/" "$task_plan_path" 2>/dev/null; then
                modified=true
            fi
        fi
    done
    if [ "$modified" = true ]; then
        # 记录 sync 事件到 JSONL
        sync_record="{\"type\":\"sync\",\"timestamp\":\"$(date '+%Y-%m-%dT%H:%M:%S')\",\"action\":\"task_plan_checkbox_auto_synced\"}"
        echo "---" >> "$history_path"
        echo "$sync_record" >> "$history_path"
    fi
fi

exit 0
