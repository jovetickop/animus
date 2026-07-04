#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
task_helpers.py — 任务辅助模块

提供任务查找、状态统计、DAG 环检测等功能。
Python 2.7+ / 3.x 兼容。
"""

from __future__ import print_function, unicode_literals
import sys


def _u(s):
    """Python 2/3 兼容：确保返回 unicode 字符串。"""
    if sys.version_info[0] < 3 and isinstance(s, str):
        return s.decode("utf-8")
    return s


def find_task_by_id(tasks, task_id):
    """按 ID 查找任务。

    Args:
        tasks: 任务列表，每个任务是包含 "id" 键的字典。
        task_id: 要查找的任务 ID（字符串）。

    Returns:
        dict or None: 找到的任务字典，未找到返回 None。
    """
    task_id_str = str(task_id)
    for task in tasks:
        if str(task.get("id", "")) == task_id_str:
            return task
    return None


def count_by_status(tasks):
    """按状态统计任务数。

    Args:
        tasks: 任务列表。

    Returns:
        dict: 格式为 {"pending": N, "in_progress": N, "passed": N,
              "failed": N, "completed": N} 的统计字典。
    """
    counts = {
        "pending": 0,
        "in_progress": 0,
        "passed": 0,
        "failed": 0,
        "completed": 0,
    }
    for task in tasks:
        status = task.get("status", "")
        if status in counts:
            counts[status] += 1
    return counts


def get_in_progress(tasks):
    """获取所有进行中的任务。

    Args:
        tasks: 任务列表。

    Returns:
        list: 状态为 "in_progress" 的任务列表，按优先级降序排列。
    """
    result = [t for t in tasks if t.get("status") == "in_progress"]

    # 按优先级降序排列
    def _priority(task):
        try:
            return int(task.get("priority", 0))
        except (TypeError, ValueError):
            return 0

    result.sort(key=_priority, reverse=True)
    return result


def validate_dag(tasks):
    """检查任务依赖是否存在环（DAG 校验）。

    使用拓扑排序（Kahn 算法）检测环。

    Args:
        tasks: 任务列表，每个任务应包含 "id" 和 "depends_on" 字段。

    Returns:
        tuple: (is_valid, cycle_info)
            - is_valid: True 表示无环，False 表示存在环。
            - cycle_info: 无环时返回空字符串，有环时返回描述信息。
    """
    # 构建任务 ID 集合
    task_ids = set()
    for task in tasks:
        tid = str(task.get("id", ""))
        if tid:
            task_ids.add(tid)

    if not task_ids:
        return True, ""

    # 构建依赖图：child -> [parents]
    # 以及入度表：node -> in_degree
    in_degree = {}
    children_map = {}  # parent -> [children]

    for tid in task_ids:
        in_degree[tid] = 0
        children_map[tid] = []

    for task in tasks:
        tid = str(task.get("id", ""))
        if not tid or tid not in task_ids:
            continue
        depends_on = task.get("depends_on", [])
        if isinstance(depends_on, list):
            for dep in depends_on:
                dep_str = str(dep).strip()
                if dep_str and dep_str in task_ids:
                    # tid 依赖于 dep_str，所以 dep_str 是 tid 的父
                    children_map.setdefault(dep_str, []).append(tid)
                    in_degree[tid] = in_degree.get(tid, 0) + 1

    # Kahn 算法
    queue = [tid for tid in task_ids if in_degree.get(tid, 0) == 0]
    sorted_count = 0

    while queue:
        node = queue.pop(0)
        sorted_count += 1
        for child in children_map.get(node, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if sorted_count == len(task_ids):
        return True, ""

    # 找出环中的节点
    cycle_nodes = [tid for tid in task_ids if in_degree.get(tid, 0) > 0]

    # 尝试描述一个环
    cycle_desc = _describe_cycle(cycle_nodes, tasks, in_degree)

    return False, cycle_desc


def _describe_cycle(cycle_nodes, tasks, in_degree):
    """描述依赖环的详细信息。"""
    if not cycle_nodes:
        return "检测到依赖环，但无法确定具体节点"

    # 从环中找一个节点作为起始点
    # 按入度降序排列，选择入度最高的
    cycle_nodes_sorted = sorted(cycle_nodes, key=lambda n: -in_degree.get(n, 0))
    start = cycle_nodes_sorted[0]

    # 尝试回溯依赖链
    task_map = {}
    for task in tasks:
        tid = str(task.get("id", ""))
        if tid:
            task_map[tid] = task

    visited = set()
    chain = []
    current = start

    while current and current in set(cycle_nodes) and current not in visited:
        visited.add(current)
        chain.append(current)

        task = task_map.get(current, {})
        depends_on = task.get("depends_on", [])
        if isinstance(depends_on, list):
            # 找第一个也在环中的依赖
            next_node = None
            for dep in depends_on:
                dep_str = str(dep).strip()
                if dep_str in set(cycle_nodes):
                    next_node = dep_str
                    break
            current = next_node
        else:
            break

    if chain:
        chain_str = " -> ".join(chain)
        # 检查首尾是否形成环
        if len(chain) > 1 and chain[-1] in set(chain[:-1]):
            # 截取环的部分
            idx = chain.index(chain[-1])
            cycle_chain = chain[idx:] + [chain[idx]]
            chain_str = " -> ".join(cycle_chain)
        return "检测到依赖环: {0}".format(chain_str)

    return "检测到依赖环，涉及节点: {0}".format(", ".join(cycle_nodes))
