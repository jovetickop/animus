#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
migrate-to-memlog.py — 一次性迁移脚本

读取当前 features.json 中的任务，为每个任务写 memlog 事件。
执行一次后不再需要。
"""

from __future__ import print_function, unicode_literals
import sys
import os

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.dirname(__file__))

# 直接导入 memlog 模块
try:
    import memlog
except ImportError:
    # 如果从项目根运行
    sys.path.insert(0, os.path.dirname(__file__))
    import memlog

import json


def migrate():
    """执行迁移：features.json → memlog"""
    animus_dir = memlog.get_animus_dir()
    if not animus_dir:
        print("错误：未找到 .claude/animus/ 目录")
        return False

    features_path = os.path.join(animus_dir, "features.json")
    if not os.path.isfile(features_path):
        print("错误：features.json 不存在")
        return False

    with open(features_path, "rb") as f:
        data = json.loads(f.read())

    # 获取任务列表
    tasks = []
    if isinstance(data, list):
        tasks = data
    elif isinstance(data, dict):
        for key in ("tasks", "initial_tasks"):
            if key in data:
                val = data[key]
                if isinstance(val, dict):
                    tasks = [{"id": tid, **tdata} for tid, tdata in val.items()]
                else:
                    tasks = val
                break

    if not tasks:
        print("features.json 中无任务数据，无需迁移")
        return True

    count = 0
    for task in tasks:
        tid = task.get("id", "")
        title = task.get("title") or task.get("name", "")
        status = task.get("status", "pending")

        # 写创建任务事件
        path = memlog.write_event("创建任务", {
            "task_id": tid,
            "title": title,
            "spec": json.dumps({
                "why": task.get("acceptance_criteria", [""])[0] if isinstance(task.get("acceptance_criteria"), list) else "",
            }, ensure_ascii=False),
        })
        if path:
            count += 1

        # 写状态事件（如果不是 pending）
        if status and status != "pending":
            path2 = memlog.write_event("状态变更", {
                "task_id": tid,
                "from": "pending",
                "to": status,
            })
            if path2:
                count += 1

    print("迁移完成：共写入 {n} 个 memlog 事件".format(n=count))
    return True


if __name__ == "__main__":
    migrate()
