#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cmd_archive.py — 归档当前迭代 (animus-engine archive)
"""

from __future__ import print_function, unicode_literals
import json
import os
import shutil
import sys
from datetime import datetime


def _find_animus_dir():
    """向上查找 .claude/animus/ 目录"""
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


def _read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read())


def _write_json(path, data):
    with open(path, "wb") as f:
        content = json.dumps(data, ensure_ascii=False, indent=2)
        if isinstance(content, str):
            f.write(content.encode("utf-8"))
        else:
            f.write(content)


def run(name="", discard=False):
    """执行归档"""
    animus_dir = _find_animus_dir()
    if not animus_dir:
        print("未找到 .claude/animus/ 目录")
        return

    archive_dir = os.path.join(animus_dir, "archive")
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    # 确定迭代编号
    existing = [d for d in os.listdir(archive_dir) if d.startswith("iter-")]
    nums = []
    for d in existing:
        parts = d.split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            nums.append(int(parts[1]))
    iteration = max(nums) + 1 if nums else 1

    if not name:
        name = "迭代 {}".format(iteration)

    # 创建迭代目录
    iter_dir = os.path.join(archive_dir, "iter-{:03d}-{}".format(iteration, name))
    os.makedirs(iter_dir)

    # 归档 memlog（移动到迭代目录，原位置清空）
    memlog_dir = os.path.join(animus_dir, "memlog")
    memlog_count = 0
    if os.path.isdir(memlog_dir):
        memlog_archive = os.path.join(iter_dir, "memlog")
        shutil.copytree(memlog_dir, memlog_archive)
        memlog_count = len([f for f in os.listdir(memlog_dir) if f.endswith(".md")])
        # 清空原 memlog
        for f in os.listdir(memlog_dir):
            fp = os.path.join(memlog_dir, f)
            if os.path.isfile(fp):
                os.remove(fp)

    # 读取当前 features.json
    features_path = os.path.join(animus_dir, "features.json")
    if os.path.isfile(features_path):
        features = _read_json(features_path)
        # 复制到归档
        shutil.copy2(features_path, os.path.join(iter_dir, "features.json"))

        # 生成迭代总结
        tasks = features.get("tasks", features.get("initial_tasks", []))
        if isinstance(tasks, dict):
            tasks = [{"id": tid, **t} for tid, t in tasks.items()]

        total = len(tasks)
        passed = sum(1 for t in tasks if t.get("status") == "passed")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        pending = sum(1 for t in tasks if t.get("status") == "pending")
        in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")

        summary = """# 迭代总结：{name}

**归档时间：** {time}
**迭代编号：** {iteration}

## 任务统计

- 总任务数：{total}
- ✅ 通过：{passed}
- ❌ 失败：{failed}
- ⏳ 待办：{pending}
- 🔄 进行中：{in_progress}

## 任务明细

""".format(name=name, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           iteration=iteration, total=total, passed=passed,
           failed=failed, pending=pending, in_progress=in_progress)

        for t in tasks:
            summary += "- [{status}] {id}: {title}\n".format(
                status=t.get("status", "?"), id=t.get("id", "?"),
                title=t.get("title", t.get("name", "?")))

        summary_path = os.path.join(iter_dir, "iteration-summary.md")
        with open(summary_path, "wb") as f:
            if isinstance(summary, str):
                f.write(summary.encode("utf-8"))
            else:
                f.write(summary)

        # 清空 features.json
        empty = {"metadata": features.get("metadata", {}), "tasks": {}}
        _write_json(features_path, empty)

        print("归档完成：{iter_dir}".format(iter_dir=iter_dir))
        print("迭代编号：{iteration}".format(iteration=iteration))
        print("已归档 {total} 个任务，{mlog} 个事件".format(total=total, mlog=memlog_count))
    else:
        print("features.json 不存在，跳过归档")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="")
    p.add_argument("--discard", action="store_true")
    args = p.parse_args()
    run(args.name, args.discard)
