#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cmd_rebuild.py — 从 memlog 重建 features.json (animus-engine rebuild)
"""

from __future__ import print_function, unicode_literals
import json
import os
import glob
import re


def _find_animus_dir():
    cwd = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(cwd, ".claude", "animus")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(cwd)
        if parent == cwd:
            break
        cwd = parent
    return None


def _write_json(path, data):
    with open(path, "wb") as f:
        content = json.dumps(data, ensure_ascii=False, indent=2)
        if isinstance(content, str):
            f.write(content.encode("utf-8"))
        else:
            f.write(content)


def run():
    """从 memlog 重建 features.json"""
    animus_dir = _find_animus_dir()
    if not animus_dir:
        print("未找到 .claude/animus/ 目录")
        return

    memlog_dir = os.path.join(animus_dir, "memlog")
    if not os.path.isdir(memlog_dir):
        print("memlog 目录不存在，无法重建")
        return

    events = sorted(glob.glob(os.path.join(memlog_dir, "*.md")))
    if not events:
        print("memlog 中没有事件，无法重建")
        return

    features = {
        "metadata": {
            "rebuilt_from": "memlog",
            "rebuilt_at": __import__("datetime").datetime.now().isoformat(),
            "event_count": len(events),
        },
        "tasks": {}
    }

    for event_path in events:
        basename = os.path.basename(event_path)
        with open(event_path, "rb") as f:
            raw = f.read().decode("utf-8")

        # 从文件名解析事件类型
        # 格式: YYYY-MM-DD-HHmm-事件类型-上下文.md
        match = re.match(
            r'\d{4}-\d{2}-\d{2}-\d{4}-(.+?)\.md$',
            basename
        )
        if not match:
            continue

        # 提取 task_id
        task_id = None
        for prefix in ["创建任务-", "状态变更-"]:
            if prefix in basename:
                # 尝试提取 Txxx 格式
                parts = basename.split("-")
                for i, p in enumerate(parts):
                    if re.match(r'^T\d+$', p):
                        task_id = p
                        break

        content_lower = raw.lower()

        if "创建任务" in content_lower or "create-task" in content_lower:
            # 提取标题
            title = "未知任务"
            for line in raw.split("\n"):
                if line.startswith("# ") and "：" in line:
                    title = line.split("：", 1)[1].strip()
                    break

            tid = task_id or "T{:03d}".format(len(features["tasks"]) + 1)
            if tid not in features["tasks"]:
                features["tasks"][tid] = {
                    "id": tid,
                    "title": title,
                    "name": title,
                    "status": "pending",
                    "depends_on": [],
                    "priority": 99,
                    "last_error": "",
                    "updated_at": basename[:16],
                }

        elif "状态变更" in content_lower or "status-change" in content_lower:
            tid = task_id
            if tid and tid in features["tasks"]:
                # 从文件名推断目标状态
                if "通过" in basename or "passed" in basename:
                    features["tasks"][tid]["status"] = "passed"
                elif "失败" in basename or "failed" in basename:
                    features["tasks"][tid]["status"] = "failed"
                elif "进行中" in basename or "in_progress" in basename:
                    features["tasks"][tid]["status"] = "in_progress"
                elif "待办" in basename or "pending" in basename:
                    features["tasks"][tid]["status"] = "pending"
                elif "完成" in basename or "completed" in basename:
                    features["tasks"][tid]["status"] = "completed"
                features["tasks"][tid]["updated_at"] = basename[:16]

        elif "归档" in content_lower or "archive" in content_lower:
            features["metadata"]["last_archive"] = basename[:16]

    # 写回 features.json
    features_path = os.path.join(animus_dir, "features.json")
    _write_json(features_path, features)

    task_count = len(features["tasks"])
    print("重建完成：从 {count} 个事件恢复了 {task_count} 个任务，已写入 features.json".format(
        count=len(events), task_count=task_count))


if __name__ == "__main__":
    run()
