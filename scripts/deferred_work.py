# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
"""
deferred-work 管理模块

审查中发现的存量问题（与本次改动无关）记入 deferred-work.md，
下次 /animus-dev 启动时自动读取作为参考，不强制。
"""

import os
import sys
from datetime import date


def get_path(animus_dir=None):
    """返回 deferred-work.md 路径"""
    if animus_dir is None:
        # 默认项目根
        base = os.path.join(os.path.dirname(os.path.dirname(__file__)))
        animus_dir = os.path.join(base, ".claude", "animus")
    return os.path.join(animus_dir, "deferred-work.md")


def read(animus_dir=None):
    """读取 deferred-work.md，返回内容（不存在返回空字符串）"""
    path = get_path(animus_dir)
    if not os.path.exists(path):
        return ""
    if sys.version_info[0] >= 3:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        with open(path, "rb") as f:
            return f.read().decode("utf-8")


def append_entry(entry, animus_dir=None):
    """追加一条 defer 记录。entry 格式："{文件路径}:{行号} {描述}" """
    path = get_path(animus_dir)
    today = date.today().isoformat()

    lines = []
    if os.path.exists(path):
        if sys.version_info[0] >= 3:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            with open(path, "rb") as f:
                lines = [l.decode("utf-8") for l in f.readlines()]

    # 检查是否已有今日标题
    has_today = any(today in l for l in lines)
    if not has_today:
        lines.append("\n## {}\n".format(today))

    lines.append("- [ ] {}\n".format(entry))

    if sys.version_info[0] >= 3:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    else:
        with open(path, "wb") as f:
            f.writelines([l.encode("utf-8") for l in lines])


def clear(animus_dir=None):
    """清空 deferred-work.md"""
    path = get_path(animus_dir)
    if sys.version_info[0] >= 3:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# 延迟工作记录\n\n")
    else:
        with open(path, "wb") as f:
            f.write("# 延迟工作记录\n\n".encode("utf-8"))


if __name__ == "__main__":
    # 简单测试
    test_dir = os.path.join(os.path.dirname(__file__), "..", ".claude", "animus")
    print("Deferred work path: {}".format(get_path(test_dir)))
    print("Current content:\n{}".format(read(test_dir)))
