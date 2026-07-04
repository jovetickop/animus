#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pre-tool-use.py — PreToolUse 钩子脚本（Python 实现）
替代 pre-tool-use.ps1，在 Write/Edit 操作前执行：
  1. 调用 write-gate.py 门控检查（非 0 则退出）
  2. 备份 .claude/animus/features.json
  3. 检查 config.toml 中 encoding=gbk，自动调用 encoding-bridge.py

用法: python pre-tool-use.py [项目根目录]
"""

from __future__ import print_function, unicode_literals

import glob
import json
import os
import shutil
import subprocess
import sys
import time


def get_script_dir():
    """返回本脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))


def main():
    script_dir = get_script_dir()

    # ============================================================
    # Step 0: 从 stdin 解析操作类型和文件路径（兼容 shell 钩子的输入格式）
    # ============================================================
    operation = ""
    file_path = ""

    try:
        if not sys.stdin.isatty():
            input_str = sys.stdin.read()
            if input_str.strip():
                data = json.loads(input_str)
                operation = data.get("tool") or data.get("name") or ""
                file_path = data.get("tool_input", {}).get("file_path") or ""
    except (ValueError, IOError, OSError):
        pass

    # 仅处理 Write/Edit 操作
    if operation not in ("Write", "Edit", ""):
        sys.exit(0)

    # 确定项目根目录
    if file_path:
        root = os.path.dirname(os.path.abspath(file_path))
        # 从目标文件向上遍历，查找 .claude/animus/
        current = root
        while True:
            candidate = os.path.join(current, ".claude", "animus", "features.json")
            if os.path.isfile(candidate):
                root = current
                break
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    elif len(sys.argv) > 1:
        root = os.path.abspath(sys.argv[1])
    else:
        root = os.getcwd()

    # ============================================================
    # Step 1: 调用 write-gate.py（门控检查）
    # ============================================================
    write_gate_path = os.path.join(script_dir, "write-gate.py")
    if os.path.isfile(write_gate_path):
        try:
            ret = subprocess.call([sys.executable, write_gate_path, root])
            if ret != 0:
                # 非 0 返回码表示阻塞，直接透传退出
                sys.exit(ret)
        except Exception as e:
            print(u"[pre-tool-use] 警告：调用 write-gate.py 失败 - {0}".format(e),
                  file=sys.stderr)
    else:
        print(u"[pre-tool-use] 警告：未找到 write-gate.py，跳过门控检查",
              file=sys.stderr)

    # ============================================================
    # Step 2: 备份 features.json（带时间戳，保留最近 5 个）
    # ============================================================
    features_path = os.path.join(root, ".claude", "animus", "features.json")
    if os.path.isfile(features_path):
        backup_dir = os.path.dirname(features_path)
        timestamp = time.strftime("%Y%m%d%H%M%S")
        backup_path = os.path.join(backup_dir, "features.json.bak.{0}".format(timestamp))
        try:
            shutil.copy2(features_path, backup_path)
            # 清理旧备份：保留最近 5 个
            all_backups = sorted(glob.glob(os.path.join(backup_dir, "features.json.bak.*")))
            while len(all_backups) > 5:
                old = all_backups.pop(0)
                try:
                    os.remove(old)
                except (IOError, OSError):
                    pass
            # 同时保留一份无时间戳的快捷备份
            simple_backup = os.path.join(backup_dir, ".features.backup.json")
            shutil.copy2(features_path, simple_backup)
        except Exception as e:
            print(u"[pre-tool-use] 警告：备份 features.json 失败 - {0}".format(e),
                  file=sys.stderr)
    else:
        print(u"[pre-tool-use] 警告：未找到 features.json，跳过备份",
              file=sys.stderr)

    # ============================================================
    # Step 3: 检查 config.toml 中 encoding=gbk
    # ============================================================
    config_path = os.path.join(root, ".claude", "animus", "config.toml")
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 兼容 "encoding=gbk" 和 'encoding = "gbk"' 两种写法
            has_gbk = ("encoding=gbk" in content or
                       'encoding = "gbk"' in content)
            if has_gbk:
                encoding_bridge_path = os.path.join(script_dir,
                                                    "encoding-bridge.py")
                if os.path.isfile(encoding_bridge_path):
                    try:
                        subprocess.call([sys.executable, encoding_bridge_path])
                    except Exception as e:
                        print(u"[pre-tool-use] 警告：调用 encoding-bridge.py "
                              u"失败 - {0}".format(e), file=sys.stderr)
                else:
                    print(u"[pre-tool-use] 警告：未找到 encoding-bridge.py，"
                          u"跳过 GBK 转换", file=sys.stderr)
        except Exception as e:
            print(u"[pre-tool-use] 警告：读取 config.toml 失败 - {0}".format(e),
                  file=sys.stderr)
    else:
        print(u"[pre-tool-use] 警告：未找到 config.toml，跳过 encoding 检查",
              file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
