#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
init_project.py — 目标项目安装脚本模板

替代 templates/init-project.ps1，创建 .claude/animus/ 目录结构，
写入初始配置文件，输出安装完成信息。
Python 2.7+ / 3.x 兼容。
"""

from __future__ import print_function, unicode_literals
import json
import os
import sys
import time


def _u(s):
    """Python 2/3 兼容：确保返回 unicode 字符串。"""
    if sys.version_info[0] < 3 and isinstance(s, str):
        return s.decode("utf-8")
    return s


def _ensure_dir(path):
    """确保目录存在，如果不存在则创建。"""
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def _write_file(path, content):
    """写入文件，兼容 Python 2/3。"""
    if sys.version_info[0] < 3:
        with open(path, "wb") as f:
            f.write(content.encode("utf-8"))
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def _file_exists(path):
    """检查文件是否存在。"""
    return os.path.exists(path)


def detect_project_type(project_root):
    """检测项目类型。"""
    cmake_path = os.path.join(project_root, "CMakeLists.txt")
    if os.path.exists(cmake_path):
        try:
            if sys.version_info[0] < 3:
                with open(cmake_path, "rb") as f:
                    content = f.read().decode("utf-8", errors="replace")
            else:
                with open(cmake_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            if "find_package" in content and "Qt" in content:
                return "cpp-qt"
        except (IOError, OSError):
            pass
        return "cpp-cmake"

    checks = {
        "Cargo.toml": "rust",
        "go.mod": "go",
        "package.json": "node",
        "pyproject.toml": "python",
        "requirements.txt": "python",
    }
    for filename, ptype in checks.items():
        if os.path.exists(os.path.join(project_root, filename)):
            return ptype
    return "generic"


def main():
    project_root = os.environ.get("CLAUDE_PROJECT_ROOT", os.getcwd())
    project_root = os.path.abspath(project_root)

    state_dir = os.path.join(project_root, ".claude", "animus")
    reports_dir = os.path.join(state_dir, "docs")
    today = time.strftime("%Y-%m-%d")

    # ============================================================
    # 步骤 1: 确定路径
    # ============================================================
    print("[步骤] 确定项目路径...")
    print("")
    print("=" * 50)
    print("  animus 项目初始化（精简模式）")
    print("=" * 50)
    print("")
    print("目标目录: {0}".format(_u(project_root)))
    print("")

    # ============================================================
    # 步骤 2: 检测项目类型
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
    # 步骤 3: 创建目录
    # ============================================================
    print("[步骤] 创建 .claude/animus 目录结构...")
    _ensure_dir(state_dir)
    _ensure_dir(reports_dir)
    print("[成功] 目录创建完成: {0}".format(_u(state_dir)))
    print("")

    # ============================================================
    # 步骤 4: 写入 README.md
    # ============================================================
    print("[步骤] 写入 README.md...")
    readme_path = os.path.join(state_dir, "README.md")

    if not _file_exists(readme_path):
        readme_content = (
            "# animus\n\n"
            "## 目录位置\n\n"
            "- **项目状态目录**: .claude/animus/（本目录）\n\n"
            "## 目录结构\n\n"
            "```\n"
            ".claude/animus/\n"
            "├── README.md                # 本文件\n"
            "├── features.json            # 任务状态列表\n"
            "├── animus-history.jsonl    # 结构化日志\n"
            "├── project-config.json      # 项目配置\n"
            "└── docs/                    # 任务报告\n"
            "```\n\n"
            "## 工作流命令\n\n"
            "### 查看状态\n"
            "```\n"
            "python scripts/show-status.py\n"
            "```\n\n"
            "### 更新任务状态\n"
            "```\n"
            "python scripts/animus-engine.py transition <TaskId> <status>\n"
            "```\n\n"
            "### 状态说明\n"
            "- `pending` - 等待执行\n"
            "- `in_progress` - 正在执行\n"
            "- `passed` - 已完成\n"
            "- `failed` - 失败\n\n"
            "## 项目类型\n\n"
            "- 类型: {0}\n".format(project_type)
        )
        _write_file(readme_path, readme_content)
        print("[信息]   README.md 已创建")
    else:
        print("[信息]   README.md 已存在，跳过")
    print("")

    # ============================================================
    # 步骤 5: 写入 project-config.json
    # ============================================================
    print("[步骤] 写入 project-config.json...")
    config_path = os.path.join(state_dir, "project-config.json")

    config = {
        "project-type": project_type,
        "detected-at": today,
        "auto-update-plugin": True,
        "verify_config": {
            "verify_enabled": False,
            "verify_command": "",
            "verify_timeout_seconds": 120,
        },
        "build-command": "",
        "test-command": "",
        "run-command": "",
    }

    # 如果文件已存在，保留已有的 build/test/run-command 值
    if _file_exists(config_path):
        try:
            if sys.version_info[0] < 3:
                with open(config_path, "rb") as f:
                    raw = f.read()
                if raw.startswith(b'\xef\xbb\xbf'):
                    raw = raw[3:]
                existing_config = json.loads(raw)
            else:
                with open(config_path, "r", encoding="utf-8-sig") as f:
                    existing_config = json.load(f)

            if isinstance(existing_config, dict):
                for key in ("build-command", "test-command", "run-command"):
                    if existing_config.get(key):
                        config[key] = existing_config[key]
                print("[信息]   project-config.json 已存在，保留已有命令值")
        except (IOError, OSError, ValueError):
            pass

    json_str = json.dumps(config, ensure_ascii=False, indent=2)
    _write_file(config_path, json_str)
    print("[成功] project-config.json 已写入")
    print("")

    # ============================================================
    # 步骤 6: 写入 features.json
    # ============================================================
    print("[步骤] 写入 features.json...")
    features_path = os.path.join(state_dir, "features.json")

    if not _file_exists(features_path):
        features = []
        json_str = json.dumps(features, ensure_ascii=False, indent=2)
        _write_file(features_path, json_str)
        print("[信息]   features.json 已创建")
    else:
        print("[信息]   features.json 已存在，跳过")
    print("")

    # ============================================================
    # 步骤 7: 写入 animus-history.jsonl
    # ============================================================
    print("[步骤] 写入 animus-history.jsonl...")
    history_path = os.path.join(state_dir, "animus-history.jsonl")

    if not _file_exists(history_path):
        _write_file(history_path, "")
        print("[信息]   animus-history.jsonl 已创建")
    else:
        print("[信息]   animus-history.jsonl 已存在，跳过")
    print("")

    # ============================================================
    # 完成
    # ============================================================
    print("=" * 50)
    print("[成功] 初始化完成！")
    print("=" * 50)
    print("")
    print("已创建:")
    print("  - {0}/README.md".format(_u(state_dir)))
    print("  - {0}/features.json".format(_u(state_dir)))
    print("  - {0}/animus-history.jsonl".format(_u(state_dir)))
    print("  - {0}/project-config.json".format(_u(state_dir)))
    print("  - {0}/docs/".format(_u(state_dir)))
    print("")
    print("项目类型: {0}".format(_u(type_names.get(project_type, project_type))))
    print("")
    print("注意: 本模式仅创建配置文件，Agent/规则/命令/Hook 等资产")
    print("      直接从技能目录读取，不再复制到项目。")
    print("")
    print("下一步:")
    print("  1. 确认构建/测试命令（编辑 project-config.json）")
    print("  2. 使用 /animus-plan 拆解任务")
    print("  3. 使用 /animus 开始工作流")
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
