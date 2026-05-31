#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
# harness-cc features.json 结构验证器 —— 含循环依赖检测

from __future__ import print_function, unicode_literals
import argparse
import json
import os
import sys


def read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        return json.loads(f.read())


def get_tasks(data):
    """从 features.json 数据中提取任务列表，支持新旧两种格式"""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "initial_tasks" in data:
            return data["initial_tasks"]
        if "tasks" in data:
            return data["tasks"]
    return []


def get_depends_on(task):
    """获取任务的依赖列表"""
    deps = task.get("depends_on", [])
    if isinstance(deps, list):
        return [str(d).strip() for d in deps if d and str(d).strip()]
    return []


def detect_circular_dependency(tasks, task_by_id):
    """
    使用拓扑排序（Kahn 算法）检测循环依赖。
    返回环中涉及的节点集合，若无环则返回空集。
    """
    # 构建入度表和邻接表
    in_degree = {}
    adjacency = {}

    for task_id in task_by_id:
        in_degree[task_id] = 0
        adjacency[task_id] = []

    for task_id, task in task_by_id.items():
        deps = get_depends_on(task)
        for dep_id in deps:
            if dep_id in task_by_id:
                # dep_id -> task_id 的边
                adjacency.setdefault(dep_id, []).append(task_id)
                in_degree[task_id] = in_degree.get(task_id, 0) + 1

    # Kahn 算法
    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    visited = 0

    while queue:
        node = queue.pop(0)
        visited += 1
        for neighbor in adjacency.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # 如果访问节点数不等于总节点数，说明有环
    in_cycle = set()
    if visited != len(task_by_id):
        for tid, deg in in_degree.items():
            if deg > 0:
                in_cycle.add(tid)

    return in_cycle


def find_cycle_path(tasks, task_by_id):
    """
    使用 DFS 查找一个具体的循环依赖路径。
    返回格式如 ['T001', 'T002', 'T003', 'T001'] 的路径，无环则返回 None。
    """
    # 构建邻接表 (depends_on 方向: dep_id -> task_id)
    adjacency = {}
    for task_id in task_by_id:
        adjacency[task_id] = []
    for task_id, task in task_by_id.items():
        deps = get_depends_on(task)
        for dep_id in deps:
            if dep_id in task_by_id:
                adjacency.setdefault(dep_id, []).append(task_id)

    visited = set()       # 已访问节点
    rec_stack = set()     # 当前递归栈中的节点
    parent = {}           # DFS 路径上的父节点

    def dfs(node, path):
        """深度优先搜索，返回发现的环路径"""
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                parent[neighbor] = node
                result = dfs(neighbor, path + [neighbor])
                if result:
                    return result
            elif neighbor in rec_stack:
                # 发现环: 从 neighbor 回溯到当前节点构建路径
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


def main():
    parser = argparse.ArgumentParser(description=u"验证 features.json 结构")
    parser.add_argument("--path", default="", help=u"features.json 路径")
    parser.add_argument("--project-root", default=".", help=u"项目根目录")
    args = parser.parse_args()

    # ============================================================
    # 确定 features.json 路径
    # ============================================================
    if args.path:
        features_path = os.path.abspath(args.path)
    else:
        project_root = os.path.abspath(args.project_root)
        features_path = os.path.join(project_root, ".claude", "state", "features.json")

    errors = []
    warnings = []

    # ============================================================
    # 检查文件是否存在
    # ============================================================
    if not os.path.exists(features_path):
        print(u"FAILED: 文件不存在: {0}".format(features_path))
        sys.exit(0)

    # ============================================================
    # 解析 JSON
    # ============================================================
    try:
        data = read_json(features_path)
    except Exception as e:
        print(u"FAILED: JSON 解析失败: {0}".format(e))
        sys.exit(0)

    # ============================================================
    # 检查根节点结构
    # ============================================================
    if not isinstance(data, (dict, list)):
        errors.append(u"根节点必须是数组或包含 tasks/initial_tasks 的字典")
        print(u"FAILED: 发现 {0} 个问题".format(len(errors)))
        for err in errors:
            print(u"  {0}".format(err))
        sys.exit(0)

    tasks = get_tasks(data)
    if not tasks:
        errors.append(u"features.json 中未找到任务列表（需要 tasks 或 initial_tasks 字段）")
        print(u"FAILED: 发现 {0} 个问题".format(len(errors)))
        for err in errors:
            print(u"  {0}".format(err))
        sys.exit(0)

    # ============================================================
    # 验证配置项（可选，但检查 verify_config 结构）
    # ============================================================
    if isinstance(data, dict) and "verify_config" in data:
        vc = data["verify_config"]
        if not isinstance(vc, dict):
            warnings.append(u"verify_config 应为字典类型")

    # ============================================================
    # 常量定义
    # ============================================================
    required_fields = [
        "id", "name", "status", "depends_on", "priority",
        "test_command", "last_error", "updated_at", "acceptance_criteria"
    ]
    # description 和 metadata 是可选的，不强制要求存在
    optional_string_fields = {"description"}
    optional_dict_fields = {"metadata"}
    valid_statuses = {"pending", "in_progress", "passed", "failed", "completed"}

    all_ids = set()
    in_progress_count = 0
    task_by_id = {}

    # ============================================================
    # 遍历检查每个任务
    # ============================================================
    for task in tasks:
        task_id = str(task.get("id", "")).strip()
        if not task_id:
            errors.append(u"[ERROR] 任务缺少 id 字段")
            continue

        # 检查必需字段
        for field in required_fields:
            if field not in task or task[field] is None:
                if field == "acceptance_criteria":
                    # acceptance_criteria 允许为空
                    continue
                errors.append(u"[ERROR] {0}: 缺少必需字段 '{1}'".format(task_id, field))

        # 检查 ID 唯一性
        if task_id in all_ids:
            errors.append(u"[ERROR] {0}: 重复的任务 ID".format(task_id))
        else:
            all_ids.add(task_id)
            task_by_id[task_id] = task

        # 检查状态值有效性
        status = str(task.get("status", "")).strip()
        if status not in valid_statuses:
            errors.append(u"[ERROR] {0}: 无效状态 '{1}'，允许值: {2}".format(
                task_id, status, ", ".join(sorted(valid_statuses))))
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

        # 检查 acceptance_criteria 格式
        ac = task.get("acceptance_criteria")
        if ac is not None and not isinstance(ac, list):
            errors.append(u"[ERROR] {0}: acceptance_criteria 必须为数组".format(task_id))

        # 检查 description（可选，如果存在则应为字符串）
        desc = task.get("description")
        if desc is not None and not isinstance(desc, (str, type(None))):
            errors.append(u"[ERROR] {0}: description 应为字符串类型".format(task_id))

        # 检查 metadata（可选，如果存在则应为字典）
        meta = task.get("metadata")
        if meta is not None:
            if not isinstance(meta, dict):
                errors.append(u"[ERROR] {0}: metadata 应为字典类型".format(task_id))
            else:
                # 检查 metadata 内部字段类型（如果存在）
                meta_created = meta.get("created_at")
                if meta_created is not None and not isinstance(meta_created, (str, type(None))):
                    errors.append(u"[ERROR] {0}: metadata.created_at 应为字符串".format(task_id))
                meta_duration = meta.get("duration_seconds")
                if meta_duration is not None and meta_duration != "":
                    try:
                        int(meta_duration)
                    except (TypeError, ValueError):
                        errors.append(u"[ERROR] {0}: metadata.duration_seconds 应为整数".format(task_id))
                meta_session = meta.get("session_id")
                if meta_session is not None and not isinstance(meta_session, (str, type(None))):
                    errors.append(u"[ERROR] {0}: metadata.session_id 应为字符串".format(task_id))

    # ============================================================
    # 检查 depends_on 引用
    # ============================================================
    for task in tasks:
        task_id = str(task.get("id", "")).strip()
        deps = get_depends_on(task)
        for dep_id in deps:
            if dep_id not in all_ids:
                errors.append(u"[ERROR] {0}: depends_on 引用了不存在的任务 '{1}'".format(task_id, dep_id))

    # ============================================================
    # 检查同一时间多个 in_progress
    # ============================================================
    if in_progress_count > 1:
        errors.append(u"[ERROR] 有 {0} 个任务处于 in_progress 状态（只允许 1 个）".format(in_progress_count))

    # ============================================================
    # P2-6: 循环依赖检测（拓扑排序 + 依赖链输出）
    # ============================================================
    if task_by_id:
        cycle_nodes = detect_circular_dependency(tasks, task_by_id)
        if cycle_nodes:
            # 尝试查找完整的循环依赖链
            cycle_path = find_cycle_path(tasks, task_by_id)
            if cycle_path and len(cycle_path) >= 2:
                # 格式: T001 -> T002 -> T003 -> T001
                chain_str = " -> ".join(cycle_path)
                errors.append(u"[ERROR] 检测到循环依赖: {0}".format(chain_str))
                # 同时将阻塞链写入警告（格式: T003 depends_on T002 depends_on T001）
                if len(cycle_path) >= 3:
                    block_chain = cycle_path[-2::-1]  # 去掉最后一个（重复的首节点）并反转
                    block_str = " depends_on ".join(block_chain)
                    warnings.append(u"阻塞链: {0}".format(block_str))
            else:
                errors.append(u"[ERROR] 检测到循环依赖，涉及任务: {0}".format(", ".join(sorted(cycle_nodes))))

    # ============================================================
    # 输出结果
    # ============================================================
    if errors:
        print(u"FAILED: 发现 {0} 个问题".format(len(errors)))
        for err in errors:
            print(u"  {0}".format(err))
    else:
        print(u"PASSED: {0} 个任务，结构验证通过".format(len(tasks)))

    if warnings:
        for warn in warnings:
            print(u"  警告: {0}".format(warn))

    sys.exit(0)


if __name__ == "__main__":
    main()
