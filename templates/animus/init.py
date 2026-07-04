#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
init.py — 目标项目首次引导

打印欢迎信息和下一步指引，检测项目类型（检查 CMakeLists.txt、Cargo.toml 等），
调用 animus-engine.py status 检查状态。
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


def detect_project_type(project_root):
    """检测项目类型。

    检查项目根目录下的标志性文件，返回项目类型字符串。
    """
    files_to_check = {
        "CMakeLists.txt": "cpp-cmake",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "package.json": "node",
        "pyproject.toml": "python",
        "requirements.txt": "python",
    }

    # 先检查 CMakeLists.txt 中是否包含 Qt
    cmake_path = os.path.join(project_root, "CMakeLists.txt")
    if os.path.exists(cmake_path):
        try:
            with open(cmake_path, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")
            if "find_package" in content and "Qt" in content:
                return "cpp-qt"
        except (IOError, OSError):
            pass
        return "cpp-cmake"

    for filename, ptype in files_to_check.items():
        if os.path.exists(os.path.join(project_root, filename)):
            return ptype

    return "generic"


def run_animus_status(state_dir):
    """调用 animus-engine.py status 检查状态。"""
    # 尝试从多个路径定位 animus-engine.py
    script_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "engine"),
    ]

    engine_script = None
    for d in script_dirs:
        candidate = os.path.join(d, "animus-engine.py")
        if os.path.exists(candidate):
            engine_script = candidate
            break

    if engine_script is None:
        # 尝试从环境变量定位
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        if plugin_root:
            candidate = os.path.join(plugin_root, "scripts", "animus-engine.py")
            if os.path.exists(candidate):
                engine_script = candidate

    if engine_script is None:
        print("[信息] 未找到 animus-engine.py，跳过状态检查")
        return

    try:
        cmd = [sys.executable, engine_script, "status"]
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print("[警告] animus-engine.py status 执行失败")
    except OSError:
        print("[警告] 无法执行 animus-engine.py")


def main():
    project_root = os.environ.get("CLAUDE_PROJECT_ROOT", os.getcwd())

    # 确保路径是绝对路径
    project_root = os.path.abspath(project_root)

    state_dir = os.path.join(project_root, ".claude", "animus")

    # ============================================================
    # 欢迎信息
    # ============================================================
    print("")
    print("=" * 50)
    print("  animus 项目初始化引导")
    print("=" * 50)
    print("")
    print("目标目录: {0}".format(_u(project_root)))
    print("")

    # ============================================================
    # 检测项目类型
    # ============================================================
    print("[步骤] 检测项目类型...")
    project_type = detect_project_type(project_root)
    type_names = {
        "cpp-qt": "C++/Qt 项目",
        "cpp-cmake": "C++/CMake 项目",
        "rust": "Rust 项目",
        "go": "Go 项目",
        "node": "Node.js 项目",
        "python": "Python 项目",
        "generic": "通用项目 (generic)",
    }
    print("[成功] 项目类型: {0}".format(_u(type_names.get(project_type, project_type))))
    print("")

    # ============================================================
    # 检查状态目录
    # ============================================================
    print("[步骤] 检查 .claude/animus/ 状态目录...")
    if os.path.isdir(state_dir):
        print("[信息] 状态目录已存在: {0}".format(_u(state_dir)))
    else:
        print("[信息] 状态目录尚未创建")
        print("[信息] 请运行 init_project.py 创建目录结构")
    print("")

    # ============================================================
    # 调用 animus-engine.py status
    # ============================================================
    print("[步骤] 调用 animus-engine.py status 检查状态...")
    run_animus_status(state_dir)
    print("")

    # ============================================================
    # 下一步指引
    # ============================================================
    print("=" * 50)
    print("下一步指引")
    print("=" * 50)
    print("")
    print("  1. 确认构建/测试命令（编辑 project-config.json）")
    print("  2. 使用 /animus-plan 拆解任务")
    print("  3. 使用 /animus 开始工作流")
    print("")
    print("项目类型: {0}".format(_u(type_names.get(project_type, project_type))))
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
