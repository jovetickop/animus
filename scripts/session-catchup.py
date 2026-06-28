#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
#
# session-catchup.py - /clear 后恢复会话上下文（5 问恢复检查）
#
# 用法:
#   python scripts/session-catchup.py [--project-dir DIR]
#
# 不再依赖 Claude Code session JSONL 文件，直接读取 .claude/harness-cc/ 状态文件。
# 输出 5 问恢复检查报告。

from __future__ import print_function, unicode_literals

import io
import json
import os
import sys
import datetime


def _ensure_utf8():
    """确保 stdout 能正常输出中文。"""
    try:
        if "PYTHONIOENCODING" not in os.environ:
            os.environ["PYTHONIOENCODING"] = "utf-8"
    except Exception:
        pass

    if sys.version_info[0] < 3:
        try:
            reload(sys)
            sys.setdefaultencoding("utf-8")
        except NameError:
            pass
    else:
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass


_ensure_utf8()


# ---------- 辅助函数 ----------

def safe_json_parse(line):
    """安全解析 JSON 行，兼容各种编码问题。"""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except (ValueError, TypeError):
        return None


def read_features(path):
    """读取 features.json → 返回 tasks 列表。

    features.json 可能是 dict（含 initial_tasks/tasks 键）或 list 格式。
    如果文件不存在或解析失败，返回 None。
    """
    if not os.path.isfile(path):
        return None
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            tasks = data.get("initial_tasks", data.get("tasks", None))
            if tasks is None:
                # 兼容直接包含 tasks 数组的 dict
                for key in ("features", "items"):
                    val = data.get(key)
                    if isinstance(val, list):
                        tasks = val
                        break
            return tasks if isinstance(tasks, list) else []
        elif isinstance(data, list):
            return data
        return []
    except (IOError, ValueError):
        return None


def read_jsonl(path):
    """读取 harness-history.jsonl → 返回 events 列表。

    每行一个 JSON 对象。如果文件不存在或解析失败，返回 None。
    """
    if not os.path.isfile(path):
        return None
    events = []
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            for line in f:
                d = safe_json_parse(line)
                if d:
                    events.append(d)
        return events
    except (IOError, ValueError):
        return None


def read_task_plan(path):
    """读取 task_plan.md → 返回文本内容。"""
    if not os.path.isfile(path):
        return None
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, ValueError):
        return None


def read_findings(path):
    """读取 findings.md → 返回文本内容。"""
    if not os.path.isfile(path):
        return None
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, ValueError):
        return None


def get_in_progress(tasks):
    """返回第一个 status=='in_progress' 的任务。"""
    for t in tasks:
        if t.get("status") == "in_progress":
            return t
    return None


def get_failed(tasks):
    """返回所有 status=='failed' 的任务。"""
    return [t for t in tasks if t.get("status") == "failed"]


def get_recent_failed_events(events, limit=3):
    """提取最近的 failed 事件（从事件列表尾部取 limit 条）。"""
    failed = [e for e in events if e.get("status") == "failed"]
    return failed[-limit:]


def get_file_mtime(path):
    """返回文件的修改时间字符串。如果文件不存在或读取出错，返回提示信息。"""
    if not path or not os.path.isfile(path):
        return u"（文件不存在）"
    try:
        ts = os.path.getmtime(path)
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return u"（无法读取）"


# ---------- 5 问输出 ----------

def print_q1(tasks):
    """[问题 1/5] 显示 in_progress 任务。"""
    print()
    print(u"【问题 1/5】当前正在处理哪个任务？")
    t = get_in_progress(tasks)
    if t:
        print(u"  当前进行中的任务:")
        print(u"    ID: {0}".format(t.get("id", "?")))
        print(u"    名称: {0}".format(t.get("name", "")))
    else:
        print(u"  当前没有进行中的任务。")


def _parse_checkbox_progress(content):
    """从 markdown 内容解析 checkbox 进度，返回 (checked, unchecked, checked_items, unchecked_items)。"""
    lines = content.split("\n")
    checked = 0
    unchecked = 0
    checked_items = []
    unchecked_items = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            checked += 1
            checked_items.append(stripped[5:].strip())
        elif stripped.startswith("- [ ]"):
            unchecked += 1
            unchecked_items.append(stripped[5:].strip())
    return checked, unchecked, checked_items, unchecked_items


def print_q2(task_plan_content):
    """[问题 2/5] 从 task_plan.md 解析进度。"""
    print()
    print(u"【问题 2/5】已完成到哪一步了？")
    if task_plan_content is None:
        print(u"  该任务未创建子步骤计划。")
        return

    checked, unchecked, checked_items, unchecked_items = _parse_checkbox_progress(task_plan_content)
    total = checked + unchecked
    if total == 0:
        # 没有 checkbox 但文件存在，显示文件内容摘要
        lines = task_plan_content.strip().split("\n")
        print(u"  文件存在但未找到勾选框格式的子步骤。")
        print(u"  文件行数: {0}".format(len(lines)))
        return

    print(u"  进度: {0}/{1} 子步骤完成".format(checked, total))
    if checked_items:
        print(u"  [已完成]")
        for item in checked_items:
            print(u"    - {0}".format(item))
    if unchecked_items:
        print(u"  [待完成]")
        for item in unchecked_items:
            print(u"    - {0}".format(item))


def print_q3(events, findings_content):
    """[问题 3/5] 显示最近失败和错误经验。"""
    print()
    print(u"【问题 3/5】最近一次失败原因？")
    if events is None:
        print(u"  无 JSONL 日志记录。")
    elif not events:
        print(u"  最近无失败记录。")
    else:
        failed_events = get_recent_failed_events(events)
        if not failed_events:
            print(u"  最近无失败记录。")
        else:
            print(u"  最近失败记录:")
            for e in failed_events:
                task_id = e.get("task_id", "?")
                msg = e.get("message", e.get("error", ""))
                print(u"    任务 {0}: {1}".format(task_id, msg))

    if findings_content:
        sections = findings_content.strip().split("\n\n")
        last_section = sections[-1].strip() if sections else ""
        if last_section:
            print(u"  错误经验（来自 findings.md）:")
            for line in last_section.split("\n")[:5]:
                print(u"    {0}".format(line.strip()))


def print_q4(paths):
    """[问题 4/5] 显示各文件修改时间。

    paths: 列表，每个元素为 (标签, 文件路径)
    """
    print()
    print(u"【问题 4/5】上下文有无变更？")
    print(u"  各状态文件的修改时间:")
    for label, filepath in paths:
        mtime = get_file_mtime(filepath)
        print(u"    {0}: {1}".format(label, mtime))


def print_q5(tasks):
    """[问题 5/5] 根据 features.json 状态给出下一步建议。"""
    print()
    print(u"【问题 5/5】下一步应该做什么？")
    if not tasks:
        print(u"  任务列表为空，请检查 features.json 。")
        return

    ip = get_in_progress(tasks)
    fl = get_failed(tasks)
    pending = [t for t in tasks if t.get("status") == "pending"]

    if ip:
        print(u"  建议: 继续当前进行中的任务（{0} — {1}）。".format(
            ip.get("id", "?"), ip.get("name", "")
        ))
    elif fl:
        for t in fl:
            print(u"  建议: 修复失败的任务（{0} — {1}）。".format(
                t.get("id", "?"), t.get("name", t.get("id", ""))
            ))
    elif pending:
        pending_sorted = sorted(pending, key=lambda t: t.get("priority", 999))
        next_task = pending_sorted[0]
        print(u"  建议: 开始最高优先级的待处理任务（{0} — {1}，优先级 {2}）。".format(
            next_task.get("id", "?"), next_task.get("name", ""),
            next_task.get("priority", "N/A")
        ))
    else:
        print(u"  建议: 所有任务已完成，准备进入下一阶段。")


def print_footer():
    """输出末尾提示。"""
    print()
    print("=" * 40)
    print(u"确认后请将理解写入 session-context.md")
    print("=" * 40)


def print_header():
    """输出报告头部。"""
    print("=" * 40)
    print(u"  5 问恢复检查")
    print("=" * 40)


# ---------- 主入口 ----------

def main():
    """主函数：解析参数、读取状态文件、输出 5 问恢复检查报告。"""
    # 解析命令行参数
    project_dir = os.getcwd()
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--project-dir" and i + 1 < len(args):
            project_dir = args[i + 1]
            i += 2
        else:
            i += 1

    # 拼装 .claude/harness-cc/ 路径
    harness_dir = os.path.join(project_dir, ".claude", "harness-cc")

    # 边界情况：harness 目录不存在
    if not os.path.isdir(harness_dir):
        print_header()
        print()
        print(u"  项目尚未初始化（.claude/harness-cc/ 目录不存在）。")
        print()
        print_footer()
        return 0

    # 定义各文件路径
    features_path = os.path.join(harness_dir, "features.json")
    jsonl_path = os.path.join(harness_dir, "harness-history.jsonl")
    task_plan_path = os.path.join(harness_dir, "task_plan.md")
    findings_path = os.path.join(harness_dir, "findings.md")

    # 读取各文件
    tasks = read_features(features_path)
    events = read_jsonl(jsonl_path)
    task_plan_content = read_task_plan(task_plan_path)
    findings_content = read_findings(findings_path)

    # 边界情况：features.json 不存在或解析失败
    if tasks is None:
        print_header()
        print()
        print(u"  未找到 features.json。")
        print()
        print_footer()
        return 0

    # 输出完整 5 问报告
    print_header()

    print_q1(tasks)
    print_q2(task_plan_content)
    print_q3(events, findings_content)
    print_q4([
        ("features.json", features_path),
        ("harness-history.jsonl", jsonl_path),
        ("task_plan.md", task_plan_path),
        ("findings.md", findings_path),
    ])
    print_q5(tasks)

    print_footer()

    return 0


if __name__ == "__main__":
    sys.exit(main())
