#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
# engine 子命令：校验 features.json 结构与一致性

from __future__ import print_function, unicode_literals
import json
import os
import sys
from collections import deque


# ============================================================
# 常量
# ============================================================
VALID_STATUSES = {"pending", "in_progress", "passed", "failed", "completed"}
REQUIRED_FIELDS = [
    "id", "name", "status", "depends_on", "priority",
    "last_error", "updated_at",
]
FEATURES_REL_PATH = os.path.join(".claude", "animus", "features.json")


# ============================================================
# 辅助函数
# ============================================================

def _read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        return json.loads(f.read())


def _get_tasks(data):
    """从 features.json 数据中提取任务列表，支持新旧两种格式。"""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "tasks" in data:
            val = data["tasks"]
            if isinstance(val, dict):
                return [dict({"id": tid}, **tdata) for tid, tdata in val.items()]
            return val
        if "initial_tasks" in data:
            val = data["initial_tasks"]
            if isinstance(val, dict):
                return [dict({"id": tid}, **tdata) for tid, tdata in val.items()]
            return val
    return []


def _get_depends_on(task):
    """获取任务的依赖列表。"""
    deps = task.get("depends_on", [])
    if isinstance(deps, list):
        return [str(d).strip() for d in deps if d and str(d).strip()]
    return []


def _detect_circular_dependency(tasks, task_by_id):
    """
    使用拓扑排序（Kahn 算法）检测循环依赖。
    返回环中涉及的节点集合，若无环则返回空集。
    """
    in_degree = {}
    adjacency = {}

    for task_id in task_by_id:
        in_degree[task_id] = 0
        adjacency[task_id] = []

    for task_id, task in task_by_id.items():
        deps = _get_depends_on(task)
        for dep_id in deps:
            if dep_id in task_by_id:
                adjacency.setdefault(dep_id, []).append(task_id)
                in_degree[task_id] = in_degree.get(task_id, 0) + 1

    # Kahn 算法
    queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
    visited = 0

    while queue:
        node = queue.popleft()
        visited += 1
        for neighbor in adjacency.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    in_cycle = set()
    if visited != len(task_by_id):
        for tid, deg in in_degree.items():
            if deg > 0:
                in_cycle.add(tid)

    return in_cycle


def _find_cycle_path(tasks, task_by_id):
    """
    使用 DFS 查找一个具体的循环依赖路径。
    返回格式如 ['T001', 'T002', 'T003', 'T001'] 的路径，无环则返回 None。
    """
    adjacency = {}
    for task_id in task_by_id:
        adjacency[task_id] = []
    for task_id, task in task_by_id.items():
        deps = _get_depends_on(task)
        for dep_id in deps:
            if dep_id in task_by_id:
                adjacency.setdefault(dep_id, []).append(task_id)

    visited = set()
    rec_stack = set()
    parent = {}

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                parent[neighbor] = node
                result = dfs(neighbor, path + [neighbor])
                if result:
                    return result
            elif neighbor in rec_stack:
                cycle = [neighbor]
                curr = node
                while curr != neighbor:
                    cycle.append(curr)
                    curr = parent.get(curr, neighbor)
                cycle.append(neighbor)
                return list(reversed(cycle))
        rec_stack.discard(node)
        return None

    for node in task_by_id:
        if node not in visited:
            result = dfs(node, [node])
            if result:
                return result
    return None


# ============================================================
# 入口
# ============================================================

def run():
    """
    校验 .claude/animus/features.json 的结构与一致性。

    检查项：
      - 文件存在性
      - JSON 解析
      - 根节点结构
      - 必需字段完整性
      - 状态值有效性
      - depends_on 引用存在性
      - 多 in_progress 冲突
      - 循环依赖
      - SPEC 字段完整性（4 法则校验）

    输出校验结果到 stdout，无返回值。
    """
    errors = []
    warnings = []

    # ----------------------------------------------------------
    # 确定 features.json 路径（从当前目录向上查找项目根目录）
    # ----------------------------------------------------------
    features_path = None
    cwd = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(cwd, FEATURES_REL_PATH)
        if os.path.isfile(candidate):
            features_path = candidate
            break
        parent = os.path.dirname(cwd)
        if parent == cwd:
            break
        cwd = parent

    if features_path is None:
        # 最后一次尝试：当前目录直连
        features_path = os.path.join(os.getcwd(), FEATURES_REL_PATH)

    # ----------------------------------------------------------
    # 检查文件是否存在
    # ----------------------------------------------------------
    if not os.path.exists(features_path):
        print(u"FAILED: 文件不存在: {0}".format(features_path))
        return

    # ----------------------------------------------------------
    # 解析 JSON
    # ----------------------------------------------------------
    try:
        data = _read_json(features_path)
    except Exception as e:
        print(u"FAILED: JSON 解析失败: {0}".format(e))
        return

    # ----------------------------------------------------------
    # 检查根节点结构
    # ----------------------------------------------------------
    if not isinstance(data, (dict, list)):
        errors.append(u"根节点必须是数组或包含 tasks/initial_tasks 的字典")
        print(u"FAILED: 发现 {0} 个问题".format(len(errors)))
        for err in errors:
            print(u"  {0}".format(err))
        return

    tasks = _get_tasks(data)
    if not tasks:
        errors.append(u"features.json 中未找到任务列表（需要 tasks 或 initial_tasks 字段）")
        print(u"FAILED: 发现 {0} 个问题".format(len(errors)))
        for err in errors:
            print(u"  {0}".format(err))
        return

    # ----------------------------------------------------------
    # 遍历检查每个任务
    # ----------------------------------------------------------
    all_ids = set()
    in_progress_count = 0
    task_by_id = {}

    for task in tasks:
        task_id = str(task.get("id", "")).strip()
        if not task_id:
            errors.append(u"[ERROR] 任务缺少 id 字段")
            continue

        # 检查必需字段
        for field in REQUIRED_FIELDS:
            if field not in task or task[field] is None:
                errors.append(u"[ERROR] {0}: 缺少必需字段 '{1}'".format(task_id, field))

        # 检查 ID 唯一性
        if task_id in all_ids:
            errors.append(u"[ERROR] {0}: 重复的任务 ID".format(task_id))
        else:
            all_ids.add(task_id)
            task_by_id[task_id] = task

        # 检查状态值有效性
        status = str(task.get("status", "")).strip()
        if status not in VALID_STATUSES:
            errors.append(u"[ERROR] {0}: 无效状态 '{1}'，允许值: {2}".format(
                task_id, status, ", ".join(sorted(VALID_STATUSES))))
        elif status == "in_progress":
            in_progress_count += 1

        # 检查 priority 为正整数
        priority = task.get("priority")
        if priority is not None:
            try:
                pval = int(priority)
                if pval <= 0:
                    errors.append(u"[ERROR] {0}: priority 必须为正整数，当前值: {1}".format(task_id, pval))
            except (TypeError, ValueError):
                errors.append(u"[ERROR] {0}: priority 必须为整数，当前值: {1}".format(task_id, priority))

        # 检查 description（可选，如果存在则应为字符串）
        desc = task.get("description")
        if desc is not None and not isinstance(desc, (str, type(None))):
            errors.append(u"[ERROR] {0}: description 应为字符串类型".format(task_id))

    # ----------------------------------------------------------
    # 检查 depends_on 引用
    # ----------------------------------------------------------
    for task in tasks:
        task_id = str(task.get("id", "")).strip()
        deps = _get_depends_on(task)
        for dep_id in deps:
            if dep_id not in all_ids:
                errors.append(u"[ERROR] {0}: depends_on 引用了不存在的任务 '{1}'".format(task_id, dep_id))

    # ----------------------------------------------------------
    # 检查同一时间多个 in_progress
    # ----------------------------------------------------------
    if in_progress_count > 1:
        errors.append(u"[ERROR] 有 {0} 个任务处于 in_progress 状态（只允许 1 个）".format(in_progress_count))

    # ----------------------------------------------------------
    # 循环依赖检测
    # ----------------------------------------------------------
    if task_by_id:
        cycle_nodes = _detect_circular_dependency(tasks, task_by_id)
        if cycle_nodes:
            cycle_path = _find_cycle_path(tasks, task_by_id)
            if cycle_path and len(cycle_path) >= 2:
                chain_str = " -> ".join(cycle_path)
                errors.append(u"[ERROR] 检测到循环依赖: {0}".format(chain_str))
                if len(cycle_path) >= 3:
                    block_chain = cycle_path[-2::-1]
                    block_str = " depends_on ".join(block_chain)
                    warnings.append(u"阻塞链: {0}".format(block_str))
            else:
                errors.append(u"[ERROR] 检测到循环依赖，涉及任务: {0}".format(", ".join(sorted(cycle_nodes))))


    # ----------------------------------------------------------
    # SPEC 字段校验（4 法则）
    # ----------------------------------------------------------
    for task in tasks:
        task_id = str(task.get("id", "?"))
        spec = task.get("spec")
        if spec is None:
            continue
        if not isinstance(spec, dict):
            errors.append("[ERROR] {0}: spec 必须是对象类型".format(task_id))
            continue

        why = spec.get("why")
        if not why or not str(why).strip():
            errors.append("[ERROR] {0}: spec.why 必须填写目的说明".format(task_id))

        caps = spec.get("capabilities")
        if not caps or not isinstance(caps, list) or len(caps) == 0:
            errors.append("[ERROR] {0}: spec.capabilities 必须为非空数组".format(task_id))

        constraints = spec.get("constraints")
        if constraints is not None and not isinstance(constraints, list):
            errors.append("[ERROR] {0}: spec.constraints 必须为数组".format(task_id))

        success = spec.get("success")
        if not success or not str(success).strip():
            errors.append("[ERROR] {0}: spec.success 必须填写可验证的成功标准".format(task_id))

    # ----------------------------------------------------------
    # 输出结果
    # ----------------------------------------------------------
    if errors:
        print(u"FAILED: 发现 {0} 个问题".format(len(errors)))
        for err in errors:
            print(u"  {0}".format(err))
    else:
        task_count = len(tasks)
        print(u"PASSED: {0} 个任务，结构验证通过".format(task_count))

    if warnings:
        for warn in warnings:
            print(u"  警告: {0}".format(warn))
    return len(errors) == 0


# ============================================================
# 模块级别 __all__ 导出
# ============================================================
__all__ = ["run"]
