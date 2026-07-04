#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pre-compact.py — PreCompact 钩子脚本（Python 实现）
替代 pre-compact.ps1。在上下文压缩前：
  1. 读取 .claude/animus/features.json
  2. 输出状态概览（总任务数/各状态计数）到 stdout
  3. 调用 show-status.py --summary（如果存在）
  4. 写入 JSONL compact 事件到 animus-history.jsonl
  5. 同步 features.json 到 task_plan.md（如果存在则追加/修改 checkbox）
  6. Append-only 检测：检查是否有任务被删除
  7. 全部失败安全（exit 0）

用法: python pre-compact.py [项目根目录]

Python 2/3 兼容。只用标准库。
"""

from __future__ import print_function, unicode_literals

import json
import os
import re
import subprocess
import sys
from datetime import datetime


def find_project_root(start_dir):
    """从 start_dir 向上查找，找到包含 .claude/animus/config.toml 的目录"""
    current = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(current, ".claude", "animus", "config.toml")
        if os.path.isfile(candidate):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def get_script_dir():
    """返回本脚本所在目录的绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))


def resolve_project_root():
    """确定项目根目录：环境变量 > 脚本路径向上查找 > 参数 > CWD"""
    env_root = os.environ.get("CLAUDE_PROJECT_ROOT")
    if env_root:
        return os.path.abspath(env_root)

    if len(sys.argv) > 1:
        return os.path.abspath(sys.argv[1])

    script_root = find_project_root(get_script_dir())
    if script_root:
        return script_root

    cwd_root = find_project_root(os.getcwd())
    if cwd_root:
        return cwd_root

    return os.getcwd()


def extract_tasks(features_data):
    """
    从 features.json 数据中提取任务列表。
    兼容三种格式:
      1. 数组: [ {...}, {...} ]
      2. 对象含 initial_tasks 或 tasks 数组: {"initial_tasks": [...]}
      3. 对象含 tasks 字典: {"tasks": {"T001": {...}, "T002": {...}}}
    """
    if isinstance(features_data, list):
        return features_data
    elif isinstance(features_data, dict):
        if "initial_tasks" in features_data and isinstance(features_data["initial_tasks"], list):
            return features_data["initial_tasks"]
        if "tasks" in features_data:
            tasks_val = features_data["tasks"]
            if isinstance(tasks_val, list):
                return tasks_val
            elif isinstance(tasks_val, dict):
                # tasks 是字典: {"T001": {...}, "T002": {...}}
                return list(tasks_val.values())
    return []


def count_statuses(tasks):
    """统计各状态的任务数量，返回 dict"""
    counts = {}
    for t in tasks:
        status = t.get("status", "unknown") if isinstance(t, dict) else "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def sync_to_task_plan(tasks, task_plan_path, history_path):
    """
    同步 features.json 中的已完成任务到 task_plan.md。
    查找 [ ] Txxx 样式的 checkbox 并标记为 [x]。
    """
    if not os.path.isfile(task_plan_path):
        return False

    try:
        with open(task_plan_path, "r") as f:
            plan_content = f.read()
    except (IOError, OSError):
        return False

    modified = False
    for task in tasks:
        if not isinstance(task, dict):
            continue
        status = task.get("status", "")
        if status not in ("passed", "completed"):
            continue
        task_id = str(task.get("id", ""))
        if not task_id:
            continue

        # 查找 [ ] 中包含该 task_id 的行
        # 支持 [ ] Txxx 和 [ ] xxx 两种格式
        escaped_id = re.escape(task_id)
        pattern = r'\[ \]([^\n]*' + escaped_id + r'[^\n]*)'
        new_content = re.sub(pattern, r'[x]\1', plan_content)
        if new_content != plan_content:
            plan_content = new_content
            modified = True

    if modified:
        try:
            with open(task_plan_path, "w") as f:
                f.write(plan_content)
            # 记录 sync 事件到 JSONL
            if history_path and os.path.isfile(history_path):
                try:
                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    sync_record = {
                        "type": "sync",
                        "timestamp": timestamp,
                        "action": "task_plan_checkbox_auto_synced"
                    }
                    with open(history_path, "a") as hf:
                        hf.write("---\n")
                        hf.write(json.dumps(sync_record, ensure_ascii=False) + "\n")
                except (IOError, OSError):
                    pass
            return True
        except (IOError, OSError):
            return False

    return False


def append_only_check(tasks, history_path):
    """
    Append-only 检测：从 JSONL 提取历史 task_id，检查是否被删除。
    """
    if not os.path.isfile(history_path):
        return

    try:
        with open(history_path, "r") as f:
            history_content = f.read()
    except (IOError, OSError):
        return

    # 解析 JSONL 中的记录（按 "---" 分隔）
    historical_ids = set()
    blocks = history_content.split("---")
    for h_block in blocks:
        h_trimmed = h_block.strip()
        if not h_trimmed:
            continue
        try:
            h_parsed = json.loads(h_trimmed)
            if "task_id" in h_parsed:
                historical_ids.add(str(h_parsed["task_id"]))
        except (ValueError, TypeError):
            continue

    if not historical_ids:
        return

    # 收集当前任务的 ID
    current_ids = set()
    for t in tasks:
        if isinstance(t, dict) and "id" in t:
            current_ids.add(str(t["id"]))

    missing_ids = [hid for hid in sorted(historical_ids) if hid not in current_ids]
    if missing_ids:
        print(u"[animus] WARNING: Append-only 违规！以下任务已从 features.json 中删除: {0}".format(
            ", ".join(missing_ids)))
        print(u"[animus] 建议从备份 features.json.bak.* 中恢复")


def main():
    project_root = resolve_project_root()

    features_path = os.path.join(project_root, ".claude", "animus", "features.json")
    history_path = os.path.join(project_root, ".claude", "animus", "animus-history.jsonl")
    task_plan_path = os.path.join(project_root, ".claude", "animus", "task_plan.md")

    # 旧路径 deprecated 警告
    old_paths = [
        os.path.join(project_root, ".claude", "state", "features.json"),
        os.path.join(project_root, ".claude", "harness", "features.json"),
    ]
    for old_path in old_paths:
        if os.path.isfile(old_path):
            print(u"[animus] WARNING: features.json 在旧路径 {0} (deprecated). 请迁移到 .claude/animus/".format(
                os.path.relpath(old_path, project_root)))

    # 1. 读取 features.json
    if not os.path.isfile(features_path):
        sys.exit(0)

    try:
        with open(features_path, "r") as f:
            features_data = json.load(f)
    except (ValueError, IOError, OSError):
        # JSON 解析失败时静默退出
        sys.exit(0)

    tasks = extract_tasks(features_data)
    total_count = len(tasks)

    if total_count == 0:
        sys.exit(0)

    # 2. 输出状态概览
    status_counts = count_statuses(tasks)
    done_count = status_counts.get("passed", 0) + status_counts.get("completed", 0)
    print(u"[animus] PreCompact: {0}/{1} 任务完成".format(done_count, total_count))

    # 输出详细状态看板
    print(u"  ├─ 总任务: {0}".format(total_count))
    for status in sorted(status_counts.keys()):
        count = status_counts[status]
        marker = "├" if status != sorted(status_counts.keys())[-1] else "└"
        print(u"  {0}─ {1}: {2}".format(marker, status, count))

    # 3. 调用 show-status.py --summary（如果存在）
    status_script = os.path.join(project_root, "templates", "animus", "show-status.py")
    if not os.path.isfile(status_script):
        status_script = os.path.join(get_script_dir(), "..", "..", "templates", "animus", "show-status.py")
        status_script = os.path.abspath(status_script)

    if os.path.isfile(status_script):
        try:
            ret = subprocess.call(
                [sys.executable, status_script,
                 os.path.join(project_root, ".claude", "animus"),
                 "--summary"],
                stdout=sys.stdout, stderr=subprocess.STDOUT
            )
        except Exception:
            pass

  
