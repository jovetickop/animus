#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
clang-format.py — PostToolUse 钩子脚本（Python 实现）
替代 clang-format.ps1。在 Write 操作完成后：
  1. 从 stdin 读取输入 JSON 对象，提取 tool_input.file_path
  2. 检查是否 C/C++ 文件，否则跳过
  3. 检查 .claude/animus/config.toml 中是否 encoding=gbk
  4. 若是 GBK 项目，先运行 encoding-bridge.py 做 GBK→UTF-8
  5. 运行 clang-format（如果系统有该工具）
  6. 若为 GBK 项目，再运行 encoding-bridge.py 做 UTF-8→GBK 回转
  7. 全部失败安全（exit 0）

用法: 从标准输入接收 JSON 对象（由 Claude Code 框架传入）

Python 2/3 兼容。只用标准库。
"""

from __future__ import print_function, unicode_literals

import json
import os
import subprocess
import sys


# C/C++ 源文件扩展名
C_EXTENSIONS = ('.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx')


def find_project_root(start_dir):
    """从 start_dir 向上查找，找到包含 .claude/animus/config.toml 的目录"""
    current = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(current, ".claude", "animus", "config.toml")
        if os.path.isfile(candidate):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def get_script_dir():
    """返回本脚本所在目录的绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))


def has_clang_format():
    """检测系统是否存在 clang-format 工具"""
    try:
        if sys.platform == "win32":
            subprocess.check_output(
                ["where", "clang-format"],
                stderr=subprocess.STDOUT,
                shell=True
            )
        else:
            subprocess.check_output(
                ["which", "clang-format"],
                stderr=subprocess.STDOUT
            )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def check_gbk_encoding(project_root):
    """
    检查项目 .claude/animus/config.toml 中是否 encoding=gbk。
    返回 True 表示需要 GBK 编码桥接。
    """
    config_path = os.path.join(project_root, ".claude", "animus", "config.toml")
    if not os.path.isfile(config_path):
        return False
    try:
        with open(config_path, "r") as f:
            content = f.read()
        # 兼容 "encoding=gbk" 和 'encoding = "gbk"' 两种写法
        return ("encoding=gbk" in content or
                'encoding = "gbk"' in content)
    except (IOError, OSError):
        return False


def run_encoding_bridge(action, file_path):
    """
    运行 encoding-bridge.py。
    action: 'to_utf8' 或 'to_gbk'
    """
    script_dir = get_script_dir()
    bridge_path = os.path.join(script_dir, "encoding-bridge.py")
    if not os.path.isfile(bridge_path):
        print(u"[clang-format] 警告：未找到 encoding-bridge.py", file=sys.stderr)
        return False
    try:
        ret = subprocess.call(
            [sys.executable, bridge_path,
             "--action", action,
             "--file", file_path]
        )
        return ret == 0
    except Exception as e:
        print(u"[clang-format] 警告：调用 encoding-bridge.py 失败 - {0}".format(e),
              file=sys.stderr)
        return False


def main():
    # 1. 从 stdin 读取输入 JSON
    try:
        raw_input_data = sys.stdin.read()
        if not raw_input_data or raw_input_data.isspace():
            sys.exit(0)
        input_obj = json.loads(raw_input_data)
    except (ValueError, IOError):
        # JSON 解析失败时静默退出
        sys.exit(0)

    # 2. 提取 file_path
    file_path = None
    try:
        file_path = input_obj.get("tool_input", {}).get("file_path", None)
    except AttributeError:
        sys.exit(0)

    if not file_path:
        sys.exit(0)

    # 统一路径分隔符
    file_path = file_path.replace("\\", "/")

    # 3. 检查是否 C/C++ 文件
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in C_EXTENSIONS:
        sys.exit(0)

    # 4. 确定项目根目录
    project_root = None
    env_root = os.environ.get("CLAUDE_PROJECT_ROOT")
    if env_root:
        project_root = os.path.abspath(env_root)
    else:
        # 从文件所在目录向上查找
        file_dir = os.path.dirname(os.path.abspath(file_path))
        project_root = find_project_root(file_dir)
        if not project_root:
            # 回退到脚本所在目录向上查找
            project_root = find_project_root(get_script_dir())

    # 5. 检查是否 GBK 编码项目
    is_gbk = False
    if project_root:
        is_gbk = check_gbk_encoding(project_root)
    else:
        # 无法确定项目根目录时也尝试查找 config.toml
        cwd_config = os.path.join(os.getcwd(), ".claude", "animus", "config.toml")
        if os.path.isfile(cwd_config):
            is_gbk = check_gbk_encoding(os.getcwd())

    # 6. 如果是 GBK 项目，先做 GBK→UTF-8 转换
    if is_gbk:
        run_encoding_bridge("to_utf8", file_path)

    # 7. 运行 clang-format
    if has_clang_format():
        try:
            ret = subprocess.call(["clang-format", "-i", file_path])
            if ret == 0:
                print(u"[clang-format] formatted: {0}".format(file_path))
            else:
                print(u"[clang-format] 警告：格式化返回码 {0}".format(ret),
                      file=sys.stderr)
        except Exception as e:
            print(u"[clang-format] 警告：运行 clang-format 失败 - {0}".format(e),
                  file=sys.stderr)
    else:
        print(u"[clang-format] 未找到 clang-format，跳过格式化", file=sys.stderr)

    # 8. 如果是 GBK 项目，做 UTF-8→GBK 回转
    if is_gbk:
        run_encoding_bridge("to_gbk", file_path)

    sys.exit(0)


if __name__ == "__main__":
    main()
