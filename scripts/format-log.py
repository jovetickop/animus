#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
#
# format-log.py — 从 JSONL 渲染人类可读的 Markdown 格式输出
#
# 用法:
#   python scripts/format-log.py [--project-dir DIR] [--recent N]
#                                [--task Txxx] [--type TYPE] [--markdown]
#
# 从 .claude/animus/animus-history.jsonl 读取事件记录，
# 支持按任务 ID、事件类型过滤和两种输出格式。

from __future__ import print_function, unicode_literals
import argparse
import io
import json
import os
import sys
import datetime

# ---------- 编码兼容层 ----------

# Windows 下修复 stdout 编码，确保中文正常输出
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


# ---------- 模块级常量 ----------
_TS_MARKDOWN_LEN = 16  # format_timestamp_markdown 截断到 "YYYY-MM-DD HH:MM"


# ---------- JSONL 读取 ----------

def read_jsonl(filepath):
    """逐行读取 JSONL 文件，返回事件列表。

    损坏行输出警告并跳过，空行跳过。
    """
    events = []

    # 尝试多种编码读取
    encodings = ["utf-8-sig", "utf-8"]
    file_content = None
    for enc in encodings:
        try:
            with io.open(filepath, "r", encoding=enc) as f:
                file_content = f.read()
            break
        except (UnicodeDecodeError, IOError):
            continue

    if file_content is None:
        try:
            with io.open(filepath, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()
        except (IOError, OSError):
            return events

    blocks = file_content.split('---\n')
    for block_num, block in enumerate(blocks, 1):
        block = block.strip()
        if not block:
            continue
        try:
            event = json.loads(block)
            events.append(event)
        except (ValueError, TypeError) as e:
            print("Warning: malformed JSON in block {}: {}".format(block_num, e),
                  file=sys.stderr)

    return events


# ---------- 格式化输出 ----------

def format_timestamp(ts):
    """格式化时间戳：截断毫秒，保留到秒。"""
    if ts is None:
        return ""
    if isinstance(ts, (int, float)):
        try:
            dt = datetime.datetime.fromtimestamp(ts)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return str(ts)
    if isinstance(ts, (str, unicode) if sys.version_info[0] < 3 else (str,)):
        # 去掉 T 分隔符和毫秒部分
        return ts.replace("T", " ").split(".")[0]
    return str(ts)


def format_timestamp_markdown(ts):
    """格式化时间戳为 Markdown 表格用：截断到分。"""
    s = format_timestamp(ts)
    if len(s) >= 16:
        return s[:_TS_MARKDOWN_LEN]
    return s


def _format_event(event, print_row):
    """共享事件类型分支逻辑。

    print_row(ts, event_type, task_id, change, message) 是格式特定的输出回调。
    """
    ts = event.get("timestamp")
    event_type = event.get("type", "")
    task_id = event.get("task_id", "") or ""
    message = event.get("message", "")

    if event_type == "state_transition":
        from_status = event.get("from_status", "")
        to_status = event.get("to_status", "")
        change = "{} → {}".format(from_status, to_status)
        exit_code = event.get("exit_code")
        if exit_code is not None and to_status == "passed":
            message = "{} [exit: {}]".format(message, exit_code)
        print_row(ts, event_type, task_id, change, message)
    elif event_type == "compact":
        print_row(ts, event_type, task_id, "", message)
    elif event_type == "note":
        print_row(ts, event_type, task_id, "", message)
    elif event_type == "subtask_update":
        print_row(ts, event_type, task_id, "", message)
    else:
        print_row(ts, event_type, task_id, "", message)


def format_plain(events):
    """输出纯文本格式（管道分隔）。"""
    def print_row(ts, event_type, task_id, change, message):
        ts_fmt = format_timestamp(ts)
        if event_type == "state_transition":
            print("{} | {} | {} | {}".format(ts_fmt, task_id, change, message))
        elif event_type == "compact":
            print("{} | [COMPACT] 上下文压缩 | {}".format(ts_fmt, message))
        elif event_type == "note":
            print("{} | [NOTE] {} | {}".format(ts_fmt, task_id, message))
        elif event_type == "subtask_update":
            print("{} | [SUBTASK] {} | {}".format(ts_fmt, task_id, message))
        elif event_type == "sync":
            print("{} | [SYNC] {} | {}".format(ts_fmt, task_id, message))
        else:
            print("{} | {} | {} | {}".format(ts_fmt, event_type, task_id, message))

    for e in events:
        _format_event(e, print_row)


def format_markdown(events):
    """输出 Markdown 表格格式。"""
    print("| 时间 | 类型 | 任务 | 变更 | 消息 |")
    print("|------|------|------|------|------|")
    def print_row(ts, event_type, task_id, change, message):
        ts_fmt = format_timestamp_markdown(ts)
        if event_type == "state_transition":
            print("| {} | state_transition | {} | {} | {} |".format(
                ts_fmt, task_id, change, message))
        else:
            print("| {} | {} | {} | | {} |".format(
                ts_fmt, event_type, task_id, message))

    for e in events:
        _format_event(e, print_row)


# ---------- 主入口 ----------

def main():
    parser = argparse.ArgumentParser(
        description="从 animus-history.jsonl 渲染人类可读的格式输出"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="项目根目录，默认当前目录",
    )
    parser.add_argument(
        "--recent",
        type=int,
        default=20,
        help="最近 N 条记录，默认为 20",
    )
    parser.add_argument(
        "--task",
        dest="task_id",
        default=None,
        help="按任务 ID 过滤（如 T001）",
    )
    parser.add_argument(
        "--type",
        dest="event_type",
        default=None,
        help="按事件类型过滤（state_transition/compact/note/subtask_update/sync）",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="输出 Markdown 表格格式",
    )

    args = parser.parse_args()

    # 构造 JSONL 文件路径
    jsonl_path = os.path.join(
        args.project_dir, ".claude", "animus", "animus-history.jsonl"
    )

    # JSONL 文件不存在时输出友好提示
    if not os.path.isfile(jsonl_path):
        print("animus-history.jsonl not found at {}".format(
            os.path.normpath(jsonl_path)
        ))
        return 0

    # 读取所有事件
    events = read_jsonl(jsonl_path)

    if not events:
        print("No events found")
        return 0

    # 过滤
    if args.event_type:
        events = [e for e in events if e.get("type") == args.event_type]
    if args.task_id:
        events = [e for e in events if e.get("task_id") == args.task_id]

    if not events:
        print("No matching events")
        return 0

    # 取最近 N 条（events 按文件顺序即时间正序，取末尾 N 条）
    if args.recent and len(events) > args.recent:
        events = events[-args.recent:]

    # 输出
    if args.markdown:
        format_markdown(events)
    else:
        format_plain(events)

    return 0


if __name__ == "__main__":
    sys.exit(main())
