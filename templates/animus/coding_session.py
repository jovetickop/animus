#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
coding_session.py — 会话入口

打印当前状态概览，读取 .claude/animus/features.json 显示任务状态，
推荐下一步命令。
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


def get_priority(task):
    """获取任务优先级，安全转换。"""
    value = task.get("priority", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def can_run(task, status_by_id):
    """判断任务依赖是否已满足。

    依赖任务状态为 passed 或 completed 时，依赖视为满足。
    """
    depends_on = task.get("depends_on", [])
    if isinstance(depends_on, list):
        for dep_id in depends_on:
            dep_id_str = str(dep_id).strip()
            if dep_id_str and status_by_id.get(dep_id_str) not in ("passed", "completed"):
                return False
    return True


def read_config(state_dir):
    """读取 project-config.json 配置。"""
    config_path = os.path.join(state_dir, "project-config.json")
    if os.path.exists(config_path):
        data = read_json(config_path)
        if isinstance(data, dict):
            return data
    return {}


def main():
    # 确定项目根目录
    project_root = os.environ.get("CLAUDE_PROJECT_ROOT", os.getcwd())
    project_root = os.path.abspath(project_root)

    state_dir = os.path.join(project_root, ".claude", "animus")
    features_path = os.path.join(state_dir, "features.json")

    # ============================================================
    # 状态概览
    # ============================================================
    print("")
    print("=" * 50)
    print("  会话状态概览")
    print("=" * 50)
    print("")
    print("项目目录: {0}".format(_u(project_root)))
    print("状态目录: {0}".format(_u(state_dir)))
    print("")

    # ============================================================
    # 读取配置
    # ============================================================
    config = read_config(state_dir)
    project_type = config.get("project-type", "unknown")
    print("项目类型: {0}".format(_u(project_type)))

    build_cmd = config.get("build-command", "")
    test_cmd = config.get("test-command", "")
    if build_cmd:
        print("构建命令: {0}".format(_u(build_cmd)))
    if test_cmd:
        print("测试命令: {0}".format(_u(test_cmd)))
    print("")

    # ============================================================
    # 任务状态
    # ============================================================
    if not os.path.exists(features_path):
        print("[提示] 未找到 features.json，跳过任务状态检查")
        print("")
        print("推荐下一步:")
        print("  1. 运行 init_project.py 初始化项目")
        print("  2. 使用 /animus-plan 拆解任务")
        print("  3. 使用 /animus 开始工作流")
        print("")
        return 0

    data = read_json(features_path)
    if data is None:
        print("[警告] features.json 解析失败")
        return 0

    tasks = get_tasks(data)
    if not tasks:
        print("[提示] features.json 中没有定义任何任务")
        return 0

    # 统计各状态
    total = len(tasks)
    passed_count = sum(1 for t in tasks if t.get("status") in ("passed", "completed"))
    failed_count = sum(1 for t in tasks if t.get("status") == "failed")
    in_progress_count = sum(1 for t in tasks if t.get("status") == "in_progress")
    pending_count = sum(1 for t in tasks if t.get("status") == "pending")

    print("任务统计 (共 {0} 个):".format(total))
    print("  [通过] passed      : {0}".format(passed_count))
    print("  [进行] in_progress : {0}".format(in_progress_count))
    print("  [待办] pending     : {0}".format(pending_count))
    print("  [失败] failed      : {0}".format(failed_count))
    print("")

    # 进度百分比
    if total > 0:
        progress_pct = int(float(passed_count) / total * 100)
        bar_filled = int(progress_pct / 100.0 * 16)
        bar_empty = 16 - bar_filled
        bar = "█" * bar_filled + "░" * bar_empty
        print("进度: {0} {1}% ({2}/{3})".format(bar, progress_pct, passed_count, total))
        print("")

    # ============================================================
    # 进行中的任务
    # ============================================================
    in_progress_tasks = [t for t in tasks if t.get("status") == "in_progress"]
    if in_progress_tasks:
        print("-" * 40)
        print("进行中的任务 (可恢复):")
        for task in in_progress_tasks:
            task_id = _u(task.get("id", ""))
            task_name = _u(task.get("name", "")) or "(未命名)"
            print("  - {0} : {1}".format(task_id, task_name))
        print("")

    # ============================================================
    # 可执行的待办任务
    # ============================================================
    status_by_id = {str(t.get("id", "")): str(t.get("status", "")) for t in tasks}
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]
    executable_pending = [t for t in pending_tasks if can_run(t, status_by_id)]
    executable_pending.sort(key=lambda t: (-get_priority(t), str(t.get("id", ""))))

    if executable_pending:
        print("-" * 40)
        print("可执行的待办任务 (依赖已满足):")
        for task in executable_pending[:5]:
            task_id = _u(task.get("id", ""))
            task_name = _u(task.get("name", "")) or "(未命名)"
            print("  - {0} : {1}".format(task_id, task_name))
        if len(executable_pending) > 5:
            print("  ... 及其他 {0} 个".format(len(executable_pending) - 5))
        print("")

    # ============================================================
    # 推荐下一步
    # ============================================================
    print("=" * 50)
    print("推荐下一步命令")
    print("=" * 50)
    print("")

    if in_progress_tasks:
        for task in in_progress_tasks:
            task_id = _u(task.get("id", ""))
            task_name = _u(task.get("name", "")) or "(未命名)"
            print("  - 继续 {0} ({1})".format(task_id, task_name))
    elif executable_pending:
        next_task = executable_pending[0]
        task_id = _u(next_task.get("id", ""))
        task_name = _u(next_task.get("name", "")) or "(未命名)"
        print("  - 开始 {0} ({1})".format(task_id, task_name))
    else:
        print("  - 使用 /animus-plan 拆解新任务")
        print("  - 使用 /animus 开始工作流")

    if build_cmd:
        print("  - 构建项目: {0}".format(_u(build_cmd)))
    if test_cmd:
        print("  - 运行测试: {0}".format(_u(test_cmd)))

    print("  - 查看详细状态: python show-status.py")
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
