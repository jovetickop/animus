#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
stop-check.py — 会话结束检查

读取 .claude/animus/features.json，检查是否有 in_progress 或 pending 任务，
有未完成任务时输出恢复提示。全部失败安全（exit 0）。
Python 2.7+ / 3.x 兼容。
"""

from __future__ import print_function, unicode_literals
import json
import os
import sys


def _u(s):
    """Python 2/3 兼容：确保返回 unicode 字符串。"""
    if sys.version_info[0] < 3 and isinstance(s, str):
        return s.decode("utf-8")
    return s


def read_json(path):
    """读取 JSON 文件，兼容 Python 2/3 以及 UTF-8 BOM。"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except (IOError, OSError):
        return None
    # 处理可能存在的 UTF-8 BOM（PowerShell 5.1 的 -Encoding UTF8 会添加 BOM）
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def get_tasks(data):
    """从 features.json 中提取任务列表，支持新旧两种格式。"""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "initial_tasks" in data:
            return data["initial_tasks"]
        if "tasks" in data:
            return data["tasks"]
    return []


def find_project_root():
    """确定项目根目录。

    优先使用环境变量 CLAUDE_PROJECT_ROOT，否则从脚本路径推导：
    <root>/.claude/hooks/scripts/ 向上三级到项目根。
    """
    env_root = os.environ.get("CLAUDE_PROJECT_ROOT")
    if env_root:
        return env_root

    # 从脚本路径推导
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # .claude/hooks/scripts/ 向上三级
    candidate = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    # 检查是否有 .claude 目录
    if os.path.isdir(os.path.join(candidate, ".claude")):
        return candidate
    # 回退到脚本所在目录的上级三级
    return candidate


def main():
    project_root = find_project_root()
    features_path = os.path.join(project_root, ".claude", "animus", "features.json")

    if not os.path.exists(features_path):
        # features.json 不存在，静默退出
        return 0

    data = read_json(features_path)
    if data is None:
        # JSON 解析失败，静默退出
        return 0

    tasks = get_tasks(data)
    if not tasks:
        return 0

    # 查找 in_progress 和 pending 任务
    in_progress_tasks = [t for t in tasks if t.get("status") == "in_progress"]
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]

    has_unfinished = bool(in_progress_tasks) or bool(pending_tasks)

    if not has_unfinished:
        return 0

    print("")
    print("=" * 50)
    print("任务状态检查")
    print("=" * 50)

    if in_progress_tasks:
        print("")
        print("以下任务正在进行中，尚未完成：")
        for task in in_progress_tasks:
            task_id = _u(task.get("id", ""))
            task_name = _u(task.get("name", "")) or "(未命名)"
            print("  - {0} : {1}".format(task_id, task_name))

        print("")
        print("【恢复建议】继续进行中的任务：")
        for task in in_progress_tasks:
            task_id = _u(task.get("id", ""))
            task_name = _u(task.get("name", "")) or "(未命名)"
            print("  继续 {0} ({1})".format(task_id, task_name))

    if pending_tasks:
        print("")
        print("以下任务等待执行（共 {0} 个）：".format(len(pending_tasks)))
        for task in pending_tasks[:5]:  # 最多显示 5 个
            task_id = _u(task.get("id", ""))
            task_name = _u(task.get("name", "")) or "(未命名)"
            print("  - {0} : {1}".format(task_id, task_name))
        if len(pending_tasks) > 5:
            print("  ... 及其他 {0} 个待办任务".format(len(pending_tasks) - 5))

    print("")
    print("请确认这些任务是否需要继续或回退状态。")
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
