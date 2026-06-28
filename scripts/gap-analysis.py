#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
#
# gap-analysis.py — 功能差距分析工具
# 读取 features.json 与预期功能列表对比，输出差距矩阵
#
# 用法:
#   python scripts/gap-analysis.py [--features PATH] [--requirements PATH]

from __future__ import print_function, unicode_literals
import argparse
import io
import json
import os
import sys


# ---------- 编码兼容 ----------
try:
    if "PYTHONIOENCODING" not in os.environ:
        os.environ["PYTHONIOENCODING"] = "utf-8"
except Exception:
    pass


# ---------- 核心逻辑 ----------

def load_features(path):
    """读取 features.json → 返回 {id: status} 字典。"""
    if not os.path.isfile(path):
        return {}
    try:
        with io.open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        tasks = data if isinstance(data, list) else data.get("tasks", data.get("initial_tasks", []))
        return {t["id"]: t.get("status", "unknown") for t in tasks if "id" in t}
    except (IOError, ValueError):
        return {}


def load_requirements(path):
    """读取需求清单文件（简单格式：每行一个功能描述，以 # 开头为注释）。"""
    if not os.path.isfile(path):
        return None
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    except (IOError, ValueError):
        return None


def print_gap_table(features, requirements):
    """输出差距分析表格。"""
    if requirements is None:
        print("功能差距分析")
        print("=" * 60)
        print("（未提供需求清单，仅展示 features.json 任务状态）")
        print()
        print("| 任务 ID | 名称 | 状态 |")
        print("|---------|------|------|")
        print()
        return

    print("功能差距分析")
    print("=" * 60)
    print()
    print("| 功能 | 状态 |")
    print("|------|------|")
    for req in requirements:
        status = features.get(req, "未定义")
        print("| {} | {} |".format(req, status))
    print()


def main():
    parser = argparse.ArgumentParser(description="功能差距分析工具")
    parser.add_argument("--features", default=".claude/harness-cc/features.json",
                        help="features.json 路径")
    parser.add_argument("--requirements", default=None,
                        help="需求清单文件路径（每行一个功能）")
    args = parser.parse_args()

    features = load_features(args.features)
    requirements = load_requirements(args.requirements) if args.requirements else None

    print_gap_table(features, requirements)

    print("分析完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
