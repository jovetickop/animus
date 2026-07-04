#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
_run_main_helpers.py — 供测试模块共享的 _run_main 辅助函数。
复制自 test_hooks.py 中的 _run_main 实现。
"""

from __future__ import print_function, unicode_literals

import io
import os
import sys


def _run_main(mod, argv, cwd=None):
    """
    在给定 argv 下运行模块的 main()，捕获 SystemExit。
    返回 (exit_code, stdout_text)。
    注意：此函数会修改 sys.argv / sys.stdout，调用者需确保串行使用。
    """
    old_argv = sys.argv[:]
    old_stdout = sys.stdout
    old_cwd = os.getcwd()
    sys.argv = argv[:]
    buf = io.StringIO()
    sys.stdout = buf
    try:
        if cwd:
            os.chdir(cwd)
        try:
            mod.main()
            code = 0
        except SystemExit as e:
            code = e.code if e.code is not None else 0
        return code, buf.getvalue()
    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
        if cwd:
            os.chdir(old_cwd)
