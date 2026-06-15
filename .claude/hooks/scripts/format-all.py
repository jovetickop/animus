#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
format-all.py — 多语言代码格式化工具

根据文件扩展名自动分发到语言特定的格式化工具。
Python 3.3+ required（依赖 subprocess.communicate 的 timeout 参数），始终以 exit 0 退出。
"""

from __future__ import print_function
import argparse
import os
import subprocess
import sys

# Cargo.toml 目录查找缓存，减少重复的向上遍历 I/O
_cargo_root_cache = {}


def find_cargo_root(start_path):
    """查找包含 Cargo.toml 的目录，使用缓存加速"""
    if start_path in _cargo_root_cache:
        return _cargo_root_cache[start_path]
    current_dir = start_path
    result = None
    while current_dir:
        if os.path.exists(os.path.join(current_dir, "Cargo.toml")):
            result = current_dir
            break
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
    _cargo_root_cache[start_path] = result
    return result


def run_formatter(cmd, file_path, formatter_name):
    """执行格式化命令，返回是否执行成功"""
    try:
        # 构造完整命令
        full_cmd = cmd + [file_path] if isinstance(cmd, list) else cmd + " " + file_path
        if isinstance(full_cmd, list):
            proc = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            proc = subprocess.Popen(
                full_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        stdout_data, stderr_data = proc.communicate(timeout=30)
        if proc.returncode == 0:
            print(u"[format-all] {0}: {1} OK".format(file_path, formatter_name))
            return True
        else:
            return False
    except Exception:
        return False


def format_py(file_path):
    """格式化 Python 文件：依次尝试 black, autopep8"""
    if run_formatter(["black", "-q", "--fast"], file_path, "black"):
        return
    if run_formatter(["autopep8", "--in-place"], file_path, "autopep8"):
        return


def format_js(file_path):
    """格式化 JavaScript/TypeScript 文件：依次尝试 prettier, eslint --fix"""
    if run_formatter(["prettier", "--write"], file_path, "prettier"):
        return
    if run_formatter(["eslint", "--fix"], file_path, "eslint"):
        return


def format_rust(file_path):
    """格式化 Rust 文件：在项目根目录执行 cargo fmt"""
    # Rust 的 cargo fmt 作用于整个项目而非单个文件
    # 查找当前文件所属项目的根目录（包含 Cargo.toml 的目录）
    current_dir = os.path.dirname(os.path.abspath(file_path))
    cargo_root = find_cargo_root(current_dir)
    if cargo_root:
        try:
            proc = subprocess.Popen(
                ["cargo", "fmt"],
                cwd=cargo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            proc.communicate(timeout=60)
            if proc.returncode == 0:
                print(u"[format-all] {0}: cargo fmt OK".format(file_path))
                return
        except Exception:
            return


def format_cpp(file_path):
    """格式化 C/C++ 文件：尝试 clang-format"""
    if run_formatter(["clang-format", "-i"], file_path, "clang-format"):
        return


def main():
    parser = argparse.ArgumentParser(description=u"多语言代码格式化工具")
    parser.add_argument("--file", required=True, help=u"要格式化的文件路径")
    args = parser.parse_args()

    file_path = args.file

    if not os.path.exists(file_path):
        print(u"[format-all] 文件不存在: {0}".format(file_path))
        sys.exit(0)

    # 根据扩展名分发
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".py":
        format_py(file_path)
    elif ext in (".js", ".ts", ".tsx", ".jsx"):
        format_js(file_path)
    elif ext == ".rs":
        format_rust(file_path)
    elif ext in (".c", ".cpp", ".h", ".hpp"):
        format_cpp(file_path)
    else:
        # 不支持的文件类型，静默跳过
        pass

    # 始终以 exit 0 退出
    sys.exit(0)


if __name__ == "__main__":
    main()
