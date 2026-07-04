#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
memlog 工具模块 — 写入和查询 append-only 事件日志。

memlog 是 animus 的单一事件源，所有状态变更先写 memlog，再重建 features.json。
memlog 永不删除，永不归档。
"""

from __future__ import print_function, unicode_literals
import os
import json
from datetime import datetime


def get_animus_dir(start_dir=None):
    """向上查找 .claude/animus/ 目录"""
    if start_dir is None:
        start_dir = os.getcwd()
    cwd = start_dir
    for _ in range(10):
        candidate = os.path.join(cwd, ".claude", "animus")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(cwd)
        if parent == cwd:
            break
        cwd = parent
    return None


def write_event(event_type, content_dict):
    """
    写入一个 memlog 事件文件。
    
    参数：
        event_type: str — 事件类型（创建任务/状态变更/决策/交接/归档/辩论）
        content_dict: dict — 事件内容
    
    返回：
        event_path: str — 写入的文件路径，失败返回 None
    """
    animus_dir = get_animus_dir()
    if not animus_dir:
        return None

    memlog_dir = os.path.join(animus_dir, "memlog")
    if not os.path.exists(memlog_dir):
        os.makedirs(memlog_dir)

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")
    iso_time = now.isoformat()

    # 从内容中提取可选上下文（用于文件名）
    context = ""
    task_id = content_dict.get("task_id", "")
    title = content_dict.get("title", content_dict.get("name", ""))
    if task_id:
        context = "-" + task_id
        if title:
            # 取前 15 个字符
            short_title = title[:15]
            context += "-" + short_title

    # 安全文件名：只保留安全字符
    safe_context = ""
    if context:
        safe_context = ""
        for ch in context:
            if ch.isalnum() or ch in ('-', '_', '.', 'T', 'P', 'C', 'D'):
                safe_context += ch
            elif '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f':
                safe_context += ch
            else:
                safe_context += '-'

    filename = "{ts}-{type}{ctx}.md".format(
        ts=timestamp,
        type=event_type,
        ctx=safe_context[:50],  # 限制文件名长度
    )
    filepath = os.path.join(memlog_dir, filename)

    # 构建文件内容
    lines = []
    lines.append("---")
    lines.append("type: {type}".format(type=event_type))
    lines.append("timestamp: {ts}".format(ts=iso_time))
    for key, val in content_dict.items():
        if key in ("type",):
            continue
        if isinstance(val, str):
            lines.append("{key}: {val}".format(key=key, val=val))
        elif isinstance(val, (list, dict)):
            lines.append("{key}: {val}".format(key=key, val=json.dumps(val, ensure_ascii=False)))
        else:
            lines.append("{key}: {val}".format(key=key, val=val))
    lines.append("---")
    lines.append("")
    lines.append("# {type}：{title}".format(type=event_type, title=title or ""))

    content = os.linesep.join(lines) + os.linesep

    try:
        with open(filepath, "wb") as f:
            f.write(content.encode("utf-8"))
        return filepath
    except (IOError, OSError) as e:
        print("写入 memlog 失败: {err}".format(err=e))
        return None


def list_events(event_type=None, limit=20):
    """
    列出 memlog 事件。
    
    参数：
        event_type: 可选事件类型过滤
        limit: 最大返回数
    
    返回：
        event list
    """
    animus_dir = get_animus_dir()
    if not animus_dir:
        return []

    memlog_dir = os.path.join(animus_dir, "memlog")
    if not os.path.isdir(memlog_dir):
        return []

    import glob
    events = sorted(glob.glob(os.path.join(memlog_dir, "*.md")))

    result = []
    for ep in events:
        basename = os.path.basename(ep)
        if event_type and event_type not in basename:
            continue
        result.append({
            "path": ep,
            "filename": basename,
        })
        if len(result) >= limit:
            break

    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3 and sys.argv[1] == "write":
        event_type = sys.argv[2]
        content = {"note": " ".join(sys.argv[3:])}
        path = write_event(event_type, content)
        if path:
            print("写入成功: {p}".format(p=path))
        else:
            print("写入失败")
    elif len(sys.argv) >= 2 and sys.argv[1] == "list":
        events = list_events()
        for e in events:
            print("  {f}".format(f=e["filename"]))
        print("共 {n} 个事件".format(n=len(events)))
    else:
        print("用法: python memlog.py write <事件类型> <内容>")
        print("      python memlog.py list")
