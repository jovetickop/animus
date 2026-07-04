#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
write-gate.py — PreToolUse 写代码门控
exit 1 = 阻塞，exit 0 = 放行
失败安全：任何解析错误 exit 0（放行）

用法: python write-gate.py [项目根目录]
"""

from __future__ import print_function, unicode_literals

import json
import os
import sys


def find_features_json(project_root):
    """返回 .claude/animus/features.json 的路径，不存在则返回 None"""
    candidate = os.path.join(project_root, ".claude", "animus", "features.json")
    if os.path.isfile(candidate):
        return candidate
    return None


def has_in_progress_tasks(features):
    """检查 features 字典中是否有 status 为 'in_progress' 的任务"""
    # 支持 tasks 和 initial_tasks 两种键名
    tasks = features.get("tasks") or features.get("initial_tasks")
    if not tasks:
        return False

    if isinstance(tasks, dict):
        for task in tasks.values():
            if isinstance(task, dict) and task.get("status") == "in_progress":
                return True
    elif isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and task.get("status") == "in_progress":
                return True

    return False


def main():
    # 确定项目根目录
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()

    project_root = os.path.abspath(project_root)

    # 查找 features.json
    features_path = find_features_json(project_root)
    if features_path is None:
        # 不存在则放行，避免误伤
        sys.exit(0)

    # 读取并解析 features.json
    try:
        with open(features_path, "r", encoding="utf-8") as f:
            features = json.load(f)
    except Exception:
        # 解析失败，放行
        sys.exit(0)

    # 检查是否有 in_progress 任务
    if has_in_progress_tasks(features):
        sys.exit(0)

    # 无 in_progress 任务，阻塞
    # safe_print 处理 Windows GBK 编码问题
    _msg1 = "\u274c 阻塞：写代码前需要先有 in_progress 任务"
    _msg2 = "   请先执行 /animus-dev 完成需求确认和任务拆分"
    try:
        print(_msg1)
        print(_msg2)
    except UnicodeEncodeError:
        print("[X] Blocked: no in_progress task found. Run /animus-dev first.", file=sys.stderr)
        print("    Run /animus-dev to confirm requirements and split tasks.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
