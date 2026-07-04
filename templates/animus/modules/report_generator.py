#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
report_generator.py — 报告生成模块

生成 Markdown 格式的状态报告和迭代归档摘要。
Python 2.7+ / 3.x 兼容。
"""

from __future__ import print_function, unicode_literals
import json
import os
import sys
import time


def _u(s):
    """Python 2/3 兼容：确保返回 unicode 字符串。"""
    if sys.version_info[0] < 3 and isinstance(s, str):
        return s.decode("utf-8")
    return s


def _safe_filename(name):
    """将字符串转换为安全的文件名。"""
    if not name or not name.strip():
        return "unnamed-task"
    safe = name.strip()
    # 替换文件名中不允许的字符
    for ch in '<>:"/\\|?*':
        safe = safe.replace(ch, "-")
    safe = safe.rstrip(".")
    if not safe:
        return "unnamed-task"
    return safe


def _get_tasks(features):
    """从 features 数据中提取任务列表。"""
    if isinstance(features, list):
        return features
    elif isinstance(features, dict):
        if "initial_tasks" in features:
            return features["initial_tasks"]
        if "tasks" in features:
            return features["tasks"]
    return []


def _status_label(status):
    """返回状态对应的中文标签。"""
    labels = {
        "passed": "通过",
        "completed": "完成",
        "failed": "失败",
        "in_progress": "进行中",
        "pending": "待办",
    }
    return labels.get(status, status)


def _status_emoji(status):
    """返回状态对应的 Emoji 图标。"""
    emojis = {
        "passed": "✅",
        "completed": "✅",
        "failed": "❌",
        "in_progress": "🟡",
        "pending": "⏳",
    }
    return emojis.get(status, "❓")


def generate_status_report(features):
    """从 features 数据生成文本状态报告。

    Args:
        features: 从 features.json 解析的 Python 对象（list 或 dict）。

    Returns:
        str: Markdown 格式的状态报告文本。
    """
    tasks = _get_tasks(features)
    if not tasks:
        return "⚠️ 未找到任何任务。\n"

    total = len(tasks)
    passed = sum(1 for t in tasks if t.get("status") in ("passed", "completed"))
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
    pending = sum(1 for t in tasks if t.get("status") == "pending")

    lines = []
    lines.append("# 任务状态报告")
    lines.append("")
    lines.append("## 统计概览")
    lines.append("")
    lines.append("| 状态 | 数量 |")
    lines.append("|------|------|")
    lines.append("| ✅ 通过 (passed) | {0} |".format(passed))
    lines.append("| ❌ 失败 (failed) | {0} |".format(failed))
    lines.append("| 🟡 进行中 (in_progress) | {0} |".format(in_progress))
    lines.append("| ⏳ 待办 (pending) | {0} |".format(pending))
    lines.append("| **总计** | **{0}** |".format(total))
    lines.append("")

    # 进度百分比
    if total > 0:
        progress_pct = int(float(passed) / total * 100)
        lines.append("**进度**: {0}% ({1}/{2})".format(progress_pct, passed, total))
        lines.append("")

    # 各任务详情
    lines.append("## 任务详情")
    lines.append("")

    for task in tasks:
        task_id = _u(task.get("id", ""))
        task_name = _u(task.get("name", "")) or "(未命名)"
        status = task.get("status", "unknown")
        priority = task.get("priority", 0)
        depends_on = task.get("depends_on", [])
        if isinstance(depends_on, list):
            depends_text = ", ".join(str(d) for d in depends_on if str(d).strip()) or "无"
        else:
            depends_text = "无"

        emoji = _status_emoji(status)
        label = _status_label(status)

        lines.append("### {0} {1} - {2}".format(emoji, task_id, task_name))
        lines.append("")
        lines.append("- **状态**: {0} ({1})".format(status, label))
        lines.append("- **优先级**: {0}".format(priority))
        lines.append("- **依赖**: {0}".format(depends_text))

        last_error = task.get("last_error", "")
        if last_error:
            lines.append("- **最后错误**: {0}".format(_u(last_error)))

        updated_at = task.get("updated_at", "")
        if updated_at:
            lines.append("- **更新时间**: {0}".format(_u(updated_at)))

        lines.append("")

    return "\n".join(lines)


def generate_iteration_summary(iteration_name, features_data, output_path):
    """生成迭代归档摘要并写入文件。

    Args:
        iteration_name: 迭代/归档名称。
        features_data: 从 features.json 解析的 Python 对象。
        output_path: 输出文件路径（Markdown 文件）。

    Returns:
        bool: 写入成功返回 True，否则返回 False。
    """
    tasks = _get_tasks(features_data)
    total = len(tasks)
    passed = sum(1 for t in tasks if t.get("status") in ("passed", "completed"))
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
    pending = sum(1 for t in tasks if t.get("status") == "pending")

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    lines = []
    lines.append("# 迭代归档: {0}".format(_u(iteration_name)))
    lines.append("")
    lines.append("> 归档时间: {0}".format(timestamp))
    lines.append("")
    lines.append("## 统计概览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append("| 总任务数 | {0} |".format(total))
    lines.append("| ✅ 通过 | {0} |".format(passed))
    lines.append("| ❌ 失败 | {0} |".format(failed))
    lines.append("| 🟡 进行中 | {0} |".format(in_progress))
    lines.append("| ⏳ 待办 | {0} |".format(pending))
    lines.append("")

    if total > 0:
        progress_pct = int(float(passed) / total * 100)
        lines.append("**完成率**: {0}%".format(progress_pct))
        lines.append("")

    lines.append("## 任务列表")
    lines.append("")
    lines.append("| ID | 名称 | 状态 | 优先级 | 依赖 |")
    lines.append("|----|------|------|--------|------|")

    for task in tasks:
        task_id = _u(task.get("id", ""))
        task_name = _u(task.get("name", "")) or "(未命名)"
        status = task.get("status", "unknown")
        priority = task.get("priority", 0)
        depends_on = task.get("depends_on", [])
        if isinstance(depends_on, list):
            depends_text = ", ".join(str(d) for d in depends_on if str(d).strip()) or "-"
        else:
            depends_text = "-"

        lines.append("| {0} | {1} | {2} | {3} | {4} |".format(
            task_id, task_name, status, priority, depends_text))

    lines.append("")

    # 写入文件
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            try:
                os.makedirs(output_dir)
            except OSError:
                pass  # 目录已存在

        content = "\n".join(lines)
        if sys.version_info[0] < 3:
            # Python 2: 写入 UTF-8 编码
            with open(output_path, "wb") as f:
                f.write(content.encode("utf-8"))
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        return True
    except (IOError, OSError) as e:
        print("[错误] 写入归档文件失败: {0}".format(_u(str(e))))
        return False
