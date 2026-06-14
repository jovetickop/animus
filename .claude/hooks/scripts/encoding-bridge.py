#!/usr/bin/env python
# encoding-bridge.py — GBK/UTF-8 编码桥接工具
# Python 2/3 兼容。在 GBK 编码的 C/C++ 项目与 UTF-8 编码的 AI 工具链之间自动转换。
#
# 用法:
#   python encoding-bridge.py --action to_utf8 --file foo.cpp [--encoding gbk]
#   python encoding-bridge.py --action to_gbk --file foo.cpp [--encoding gbk]
#
# to_utf8:  读取 GBK/指定编码文件 -> 以 UTF-8 写入
# to_gbk:   读取 UTF-8 文件 -> 以 GBK/指定编码写入
# 仅处理 C/C++ 源文件，跳过大于 5MB 的文件

from __future__ import print_function
import os
import sys

# 仅处理 C/C++ 源文件扩展名
C_EXTENSIONS = ('.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx')
# 跳过大于 5MB 的文件
MAX_SIZE = 5 * 1024 * 1024


def get_encoding(args):
    """从命令行参数中提取 --encoding 值，默认返回 gbk"""
    for i, arg in enumerate(args):
        if arg == '--encoding' and i + 1 < len(args):
            return args[i + 1]
    return 'gbk'


def get_action(args):
    """提取 --action 参数值（to_utf8 或 to_gbk）"""
    for i, arg in enumerate(args):
        if arg == '--action' and i + 1 < len(args):
            return args[i + 1]
    return None


def get_file(args):
    """提取 --file 参数值（文件路径）"""
    for i, arg in enumerate(args):
        if arg == '--file' and i + 1 < len(args):
            return args[i + 1]
    return None


def to_utf8(file_path, encoding):
    """
    将指定编码（如 GBK）的文件转换为 UTF-8。
    以二进制读取，按指定编码解码后写回 UTF-8。

    返回 True 表示转换成功，False 表示失败。
    """
    try:
        with open(file_path, 'rb') as f:
            raw = f.read()
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            return False
        with open(file_path, 'wb') as f:
            f.write(text.encode('utf-8'))
        return True
    except (IOError, OSError) as e:
        print(u"[encoding-bridge] 转换失败 {0}: {1}".format(file_path, e), file=sys.stderr)
        return False


def to_gbk(file_path, encoding):
    """
    将 UTF-8 文件转换为指定编码（如 GBK）。
    以二进制读取 UTF-8，解码后按目标编码写回。

    返回 True 表示转换成功，False 表示失败。
    """
    try:
        with open(file_path, 'rb') as f:
            raw = f.read()
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            return False
        with open(file_path, 'wb') as f:
            f.write(text.encode(encoding))
        return True
    except (IOError, OSError) as e:
        print(u"[encoding-bridge] 转换失败 {0}: {1}".format(file_path, e), file=sys.stderr)
        return False


def main():
    """主入口：解析参数并执行对应的编码转换"""
    action = get_action(sys.argv)
    file_path = get_file(sys.argv)
    enc = get_encoding(sys.argv)

    if not action or not file_path:
        sys.exit(0)

    # 检查文件扩展名，非 C/C++ 文件跳过
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in C_EXTENSIONS:
        sys.exit(0)

    # 跳过过大文件
    try:
        if os.path.getsize(file_path) > MAX_SIZE:
            sys.exit(0)
    except OSError:
        sys.exit(0)

    if action == 'to_utf8':
        to_utf8(file_path, enc)
    elif action == 'to_gbk':
        to_gbk(file_path, enc)

    sys.exit(0)


if __name__ == '__main__':
    main()
