#!/usr/bin/env python
# -*- coding: utf-8 -*-
# cmd_status.py — /animus-status 后端逻辑
# 读取 .claude/animus/features.json 并输出任务状态统计
# 兼容 Python 2.7+ 和 3.x

from __future__ import print_function, unicode_literals
import json
import os
import sys

# ---------- deferred-work ----------

def _count_deferred(features_dir):
    """统计 deferred-work.md 中的待办条目数"""
    dw_path = os.path.join(features_dir, "deferred-work.md")
    if not os.path.isfile(dw_path):
        return 0
    try:
        with open(dw_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content.count("- [ ]")
    except Exception:
        return 0

# ---------- 工作流依赖图 ----------

WORKFLOW_GRAPH = {
    "animus-init": {
        "pre": [],
        "post": [".claude/animus/features.json 存在"],
        "next": ["animus-dev"],
    },
    "animus-dev": {
        "pre": [".claude/animus/features.json 存在"],
        "post": ["features.json 有 in_progress 任务"],
        "next": ["animus-review", "animus-status"],
    },
    "animus-review": {
        "pre": ["features.json 有 passed 任务"],
        "post": ["审查报告已生成"],
        "next": ["animus-archive"],
    },
    "animus-archive": {
        "pre": ["所有任务已完成"],
        "post": ["features.json 已清空"],
        "next": ["animus-dev"],
    },
    "animus-status": {
        "pre": [],
        "post": [],
        "next": [],
    },
    "animus-help": {
        "pre": [],
        "post": [],
        "next": [],
    },
    "animus-party": {
        "pre": [],
        "post": [],
        "next": [],
    },
}


def _recommend_next(features):
    """根据 features.json 当前状态推荐下一步。返回 (命令, 理由)。"""
    if not features:
        return ("/animus-init", "项目还没初始化，先运行 init")

    # 获取任务列表
    tasks_data = features.get("tasks", features.get("initial_tasks", []))
    tasks = []
    if isinstance(tasks_data, dict):
        tasks = [{"id": tid, **t} for tid, t in tasks_data.items()]
    elif isinstance(tasks_data, list):
        tasks = tasks_data

    if not tasks:
        return ("/animus-dev", "还没有任务，开始规划第一个功能")

    has_pending = any(t.get("status") == "pending" for t in tasks)
    has_in_progress = any(t.get("status") == "in_progress" for t in tasks)
    has_passed = any(t.get("status") == "passed" for t in tasks)
    has_failed = any(t.get("status") == "failed" for t in tasks)
    all_done = all(t.get("status") in ("passed", "completed") for t in tasks)

    if has_in_progress:
        return ("/animus-dev", "有进行中的任务，继续实施")
    if has_failed:
        return ("/animus-dev", "有失败的任务，修复后重试")
    if has_pending:
        return ("/animus-dev", "有待办任务，开始实施")
    if has_passed and not all_done:
        return ("/animus-review", "有已完成任务，需要审查")
    if all_done:
        return ("/animus-archive", "所有任务已完成，归档迭代")

    return ("/animus-dev", "开始新的开发")


def _text(value):
    """将值强制转为 str（Python 2 下为字节串，Python 3 下为文本）。"""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _find_features_json():
    """按优先级搜索 features.json 文件路径。"""
    # 1) 环境变量显式指定
    env_path = os.environ.get("ANIMUS_FEATURES_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2) 当前目录下的 .claude/animus/features.json
    candidates = [
        os.path.join(".claude", "animus", "features.json"),
        os.path.join(".claude", "state", "features.json"),
    ]

    # 3) 脚本所在目录向上查找
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for parent in (script_dir, os.path.join(script_dir, "..", ".."),
                   os.path.join(script_dir, "..", "..", "..")):
        candidates.append(os.path.join(parent, ".claude", "animus", "features.json"))
        candidates.append(os.path.join(parent, ".claude", "state", "features.json"))

    for path in candidates:
        normalized = os.path.normpath(path)
        if os.path.isfile(normalized):
            return normalized

    return None


def _read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        return json.load(f)


def _extract_tasks(data):
    """从 features.json 数据中提取任务列表，支持多种格式。"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("initial_tasks", "tasks", "features"):
            if key in data:
                val = data[key]
                if isinstance(val, dict):
                    return [{"id": tid, **tdata} for tid, tdata in val.items()]
                return val
        # 如果只有一个顶层任务对象（如 {"id":"T001",...}），包装成列表
        if "id" in data:
            return [data]
    return []


def run():
    """/animus-status 主逻辑。返回格式化字符串。"""
    result_lines = []
    append = result_lines.append

    features_path = _find_features_json()
    if not features_path:
        append("ERROR: 未找到 features.json（查找路径：.claude/animus/features.json）")
        return "\n".join(result_lines)

    try:
        data = _read_json(features_path)
    except (ValueError, IOError) as e:
        append("ERROR: 读取 features.json 失败: {0}".format(_text(e)))
        return "\n".join(result_lines)

    tasks = _extract_tasks(data)
    features_dir = os.path.dirname(features_path)
    deferred_count = _count_deferred(features_dir)
    if not tasks:
        append("INFO: features.json 中无任务数据")
        return "\\n".join(result_lines)

    # ---- 统计 ----
    total = len(tasks)
    statuses = {}
    for task in tasks:
        s = _text(task.get("status", "unknown")).lower()
        statuses[s] = statuses.get(s, 0) + 1

    passed = statuses.get("passed", 0)
    failed = statuses.get("failed", 0)
    pending = statuses.get("pending", 0)
    in_progress = statuses.get("in_progress", 0)
    skipped = statuses.get("skipped", 0)
    other = total - passed - failed - pending - in_progress - skipped

    # ---- 输出标题 ----
    append("=" * 54)
    append("  Animus — 任务状态报告")
    append("=" * 54)
    append("")

    # ---- 输出统计 ----
    append(u"  \u7edf\u8ba1\u6982\u89c8")
    append(u"  \u2500" * 27)
    append(u"  \u603b\u4efb\u52a1\u6570  : {0}".format(total))
    append(u"  \u2713 \u5df2\u901a\u8fc7    : {0}".format(passed))
    append(u"  \u2717 \u5931\u8d25    : {0}".format(failed))
    append(u"  \u25e6 \u5f85\u529e\u4e8b\u9879 : {0}".format(pending))
    append(u"  \u25b6 \u8fdb\u884c\u4e2d : {0}".format(in_progress))
    if skipped:
        append(u"  \u23f8 \u8df3\u8fc7    : {0}".format(skipped))
    if other:
        append(u"  ? \u5176\u4ed6    : {0}".format(other))
    append("")

    # ---- 输出每个任务明细 ----
    append(u"  \u4efb\u52a1\u660e\u7ec6")
    append(u"  \u2500" * 27)

    # 状态排序优先级
    STATUS_ORDER = {
        "in_progress": 0,
        "failed": 1,
        "pending": 2,
        "passed": 3,
        "skipped": 4,
    }

    sorted_tasks = sorted(
        tasks,
        key=lambda t: (
            STATUS_ORDER.get(_text(t.get("status", "")).lower(), 99),
            _text(t.get("id", "")),
        ),
    )

    for task in sorted_tasks:
        tid = _text(task.get("id", "?"))
        tname = _text(task.get("name", ""))
        tstatus = _text(task.get("status", "unknown"))
        # 用 ASCII 标记标记状态
        icon_map = {
            "passed": "[PASS]",
            "failed": "[FAIL]",
            "pending": "[PEND]",
            "in_progress": "[RUN ]",
            "skipped": "[SKIP]",
        }
        icon = icon_map.get(tstatus.lower(), "[?]")
        append(u"  {icon} [{tid}] {name} ({status})".format(
            icon=icon, tid=tid, name=tname, status=tstatus
        ))

    append("")
    append("=" * 54)
    append("")
    append(u"  \u2728 \u63a8\u8350\u4e0b\u4e00\u6b65\uff1a")
    if isinstance(data, dict):
        cmd, reason = _recommend_next(data)
        append(u"     {0}  \u2014 {1}".format(cmd, reason))

    return "\n".join(result_lines)


if __name__ == "__main__":
    output = run()
    print(output)
    if output.startswith("ERROR"):
        sys.exit(1)
