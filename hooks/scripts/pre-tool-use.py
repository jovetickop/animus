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

import os
import shutil
import subprocess
import sys


def get_script_dir():
    """返回本脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))


def main():
    # 确定项目根目录
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.getcwd()
    root = os.path.abspath(root)

    script_dir = get_script_dir()

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
    # Step 2: 备份 features.json → .features.backup.json
    # ============================================================
    features_path = os.path.join(root, ".claude", "animus", "features.json")
    if os.path.isfile(features_path):
        backup_path = os.path.join(root, ".claude", "animus",
                                   ".features.backup.json")
        try:
            shutil.copy2(features_path, backup_path)
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
