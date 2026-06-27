#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容

from __future__ import print_function
import json
import os
import sys


def get_priority(task):
    value = task.get("priority", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_depends_on(task):
    depends_on = task.get("depends_on", [])
    if isinstance(depends_on, list):
        return [str(item) for item in depends_on if str(item).strip()]
    return []


def can_run(task, status_by_id):
    """判断任务依赖是否已满足。

    状态机契约：依赖任务状态为 passed 或 completed 时，依赖视为满足。
    与 PowerShell 版 pre-compact.ps1:43 和 pre-compact.sh:30 保持一致。
    """
    for dep_id in get_depends_on(task):
        if status_by_id.get(dep_id) not in ("passed", "completed"):
            return False
    return True


def read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        return json.load(f)


def get_tasks(data):
    """从 features.json 中提取任务列表，支持新旧两种格式"""
    if isinstance(data, list):
        # 旧格式：直接是任务数组
        return data
    elif isinstance(data, dict):
        # 新格式：有 initial_tasks 字段
        if "initial_tasks" in data:
            return data["initial_tasks"]
        # 也支持 tasks 字段
        if "tasks" in data:
            return data["tasks"]
    return []


def main():
    if len(sys.argv) > 1:
        state_root = sys.argv[1]
    else:
        default_root = os.path.join(".claude", "state")
        if os.path.exists(default_root):
            state_root = default_root
        else:
            state_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state")

    features_path = os.path.join(state_root, "features.json")

    if not os.path.exists(features_path):
        print(u"未找到 features.json: {0}".format(features_path))
        return 1

    data = read_json(features_path)
    tasks = get_tasks(data)
    status_by_id = {str(task.get("id", "")): str(task.get("status", "")) for task in tasks}

    total = len(tasks)
    passed = sum(1 for task in tasks if task.get("status") == "passed")
    completed = sum(1 for task in tasks if task.get("status") == "completed")
    passed = passed + completed  # 合并计算
    failed_tasks = [task for task in tasks if task.get("status") == "failed"]
    in_progress = None
    for task in tasks:
        if task.get("status") == "in_progress":
            in_progress = task
            break
    pending_tasks = [task for task in tasks if task.get("status") == "pending"]

    executable_pending = [task for task in pending_tasks if can_run(task, status_by_id)]
    executable_pending.sort(key=lambda task: (-get_priority(task), str(task.get("id", ""))))
    next_pending = executable_pending[0] if executable_pending else None

    # --- 显示 Oracle 验证门配置状态 ---
    verify_config = data.get("verify_config") if isinstance(data, dict) else None
    if verify_config:
        enabled = verify_config.get("verify_enabled", False)
        cmd = verify_config.get("verify_command", "")
        timeout = verify_config.get("verify_timeout_seconds", 120)
        status_text = u"已启用" if enabled else u"未启用"
        cmd_text = cmd if cmd else u"(无)"
        print(u"Oracle 验证门: {0} | 命令: {1} | 超时: {2}s".format(status_text, cmd_text, timeout))

    print(u"")
    print(u"任务总数: {0}".format(total))
    print(u"已通过: {0}".format(passed))
    print(u"失败: {0}".format(len(failed_tasks)))

    if in_progress:
        task_id = in_progress.get("id", "UNKNOWN")
        task_name = in_progress.get("name", "")
        updated_at = in_progress.get("updated_at", "")
        print(u"进行中: {0} {1}".format(task_id, task_name))
        if updated_at:
            print(u"进行中更新时间: {0}".format(updated_at))
    elif next_pending:
        task_id = next_pending.get("id", "UNKNOWN")
        task_name = next_pending.get("name", "")
        priority = get_priority(next_pending)
        print(u"下一个可执行任务: {0} {1} (priority={2})".format(task_id, task_name, priority))

        blocked = len(pending_tasks) - len(executable_pending)
        if blocked > 0:
            print(u"被依赖阻塞的 pending 任务: {0}".format(blocked))
    else:
        print(u"所有任务均已完成。")

    if failed_tasks:
        failed_tasks.sort(key=lambda task: (-get_priority(task), str(task.get("id", ""))))
        top_failed = failed_tasks[0]
        err = str(top_failed.get("last_error", "")).strip()
        task_id = top_failed.get("id", "UNKNOWN")
        task_name = top_failed.get("name", "")
        print(u"待处理失败任务: {0} {1}".format(task_id, task_name))
        if err:
            print(u"最近失败原因: {0}".format(err))

    return 0


if __name__ == "__main__":
    sys.exit(main())

