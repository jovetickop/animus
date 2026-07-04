#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
git_helper.py — Git 辅助模块

提供 Git 自动提交、分支获取、变更检查等辅助功能。
Python 2.7+ / 3.x 兼容。
"""

from __future__ import print_function, unicode_literals
import os
import subprocess
import sys


def _u(s):
    """Python 2/3 兼容：确保返回 unicode 字符串。"""
    if sys.version_info[0] < 3 and isinstance(s, str):
        return s.decode("utf-8")
    return s


def _run_git(args):
    """执行 Git 命令，返回 (returncode, stdout, stderr)。"""
    cmd = ["git"] + args
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        # Python 2/3 兼容：统一为字符串
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return proc.returncode, stdout, stderr
    except OSError as e:
        return -1, "", _u("无法执行 git: {0}").format(e)


def is_git_repo():
    """检查当前目录是否在 Git 仓库中。"""
    retcode, _, _ = _run_git(["rev-parse", "--is-inside-work-tree"])
    return retcode == 0


def commit_changes(msg):
    """提交所有变更。

    执行 git add -A && git commit -m <msg>。
    仅在 Git 仓库中有效。

    Args:
        msg: 提交信息字符串。

    Returns:
        bool: 提交成功返回 True，否则返回 False。
    """
    if not is_git_repo():
        print("[信息] 非 Git 仓库，跳过自动提交")
        return False

    # git add -A
    retcode, stdout, stderr = _run_git(["add", "-A"])
    if retcode != 0:
        print("[错误] git add 失败: {0}".format(_u(stderr)))
        return False

    # 检查是否有变更可提交
    retcode, _, _ = _run_git(["diff", "--cached", "--quiet"])
    if retcode == 0:
        # 无变更
        return True

    # git commit -m msg
    retcode, stdout, stderr = _run_git(["commit", "-m", msg])
    if retcode != 0:
        print("[错误] git commit 失败: {0}".format(_u(stderr)))
        return False

    print("[成功] 已提交: {0}".format(_u(msg)))
    return True


def get_current_branch():
    """获取当前分支名称。

    Returns:
        str: 分支名称，获取失败返回 None。
    """
    retcode, stdout, stderr = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if retcode != 0:
        return None
    branch = stdout.strip()
    return branch if branch else None


def has_uncommitted_changes():
    """检查是否有未提交的变更。

    Returns:
        bool: 有未提交变更返回 True，否则返回 False。
    """
    if not is_git_repo():
        return False

    # 检查工作区变更
    retcode, stdout, _ = _run_git(["status", "--porcelain"])
    if retcode != 0:
        return False

    return bool(stdout.strip())
