#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
animus_init.py — 初始化项目 .claude/animus/ 配置

用法:
    python animus_init.py [项目根目录]

替代 commands/animus-init.ps1 的 Python 实现。
Python 2/3 兼容。
"""

from __future__ import print_function, unicode_literals

import json
import os
import sys
import time

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

FEATURES_JSON_TEMPLATE = {
    "version": 1,
    "tasks": [],
    "created_at": None,  # 写入时填入
    "updated_at": None,  # 写入时填入
}

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _now_iso():
    """返回 ISO 格式时间戳 (YYYY-MM-DDTHH:MM:SS)"""
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _write_json(path, obj):
    """以 UTF-8 写入 JSON 文件（Python 2/3 兼容）。"""
    text = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False)
    if sys.version_info[0] >= 3:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        with open(path, "wb") as f:
            f.write(text.encode("utf-8"))


def _read_json(path):
    """以 UTF-8 读取 JSON 文件（Python 2/3 兼容）。"""
    if sys.version_info[0] >= 3:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        with open(path, "rb") as f:
            return json.loads(f.read().decode("utf-8"))


def _write_text(path, text):
    """以 UTF-8 写入文本文件（Python 2/3 兼容）。"""
    if sys.version_info[0] >= 3:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        with open(path, "wb") as f:
            f.write(text.encode("utf-8"))


def _read_text(path):
    """以 UTF-8 读取文本文件（Python 2/3 兼容）。"""
    if sys.version_info[0] >= 3:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        with open(path, "rb") as f:
            return f.read().decode("utf-8")


def _path_exists(path):
    """兼容 os.path.exists。"""
    return os.path.exists(path)


# ---------------------------------------------------------------------------
# TOML 写入（简单实现，不依赖外部包）
# ---------------------------------------------------------------------------

def _toml_value(value):
    """将 Python 值序列化为 TOML 值字面量。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    # 字符串
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return '"{}"'.format(escaped)


def _write_toml(path, sections):
    """
    写入 TOML 配置文件。

    sections = {
        "project": {
            "type": "cpp-qt",
            "build_command": "",
            ...
        },
        "project.verify": {
            "enabled": False,
            ...
        }
    }
    """
    lines = []
    for section_key, kv in sections.items():
        lines.append("[{}]".format(section_key))
        for k, v in kv.items():
            lines.append("{} = {}".format(k, _toml_value(v)))
        lines.append("")
    _write_text(path, "\n".join(lines[:-1]) + "\n")  # 去掉末尾多余空行，只留一个


# ---------------------------------------------------------------------------
# 项目类型检测
# ---------------------------------------------------------------------------

def _file_exists(root, name):
    return _path_exists(os.path.join(root, name))


def detect_project_type(project_root):
    """
    检测项目类型，按优先级：
    CMakeLists.txt (含 Qt → cpp-qt) > Cargo.toml > go.mod > package.json >
    pyproject.toml/requirements.txt > generic
    """
    cmake = os.path.join(project_root, "CMakeLists.txt")
    if _path_exists(cmake):
        content = _read_text(cmake)
        if "find_package(Qt" in content:
            return "cpp-qt"
        return "cpp-cmake"

    if _file_exists(project_root, "Cargo.toml"):
        return "rust"

    if _file_exists(project_root, "go.mod"):
        return "go"

    if _file_exists(project_root, "package.json"):
        return "node"

    if _file_exists(project_root, "pyproject.toml") or _file_exists(project_root, "requirements.txt"):
        return "python"

    return "generic"


# ---------------------------------------------------------------------------
# 配置模板


def detect_sub_projects(project_root):
    """扫描一级子目录，检测各子项目类型。返回 [(dir_name, type), ...]"""
    sub_projects = []
    if not os.path.isdir(project_root):
        return sub_projects
    try:
        entries = sorted(os.listdir(project_root))
    except Exception:
        return sub_projects
    for entry in entries:
        subdir = os.path.join(project_root, entry)
        if not os.path.isdir(subdir) or entry.startswith("."):
            continue
        sub_type = detect_project_type(subdir)
        if sub_type != "generic":
            sub_projects.append((entry, sub_type))
    return sub_projects

# ---------------------------------------------------------------------------

def _make_project_config(project_type, sub_projects=None):
    """根据项目类型生成 [project] 配置。"""
    config = {
        "type": project_type,
        "build_command": "",
        "test_command": "",
        "run_command": "",
        "auto_update_plugin": True,
    }
    if sub_projects:
        config["sub_projects"] = [{"dir": d, "type": t} for d, t in sub_projects]
    return config


def _make_full_toml(project_type, sub_projects=None):
    """生成完整的 config.toml 内容（含注释头）。"""
    sections = {
        "project": _make_project_config(project_type, sub_projects),
    }
    return sections


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def animus_init(project_root):
    """
    执行 animus 初始化。
    返回 True 表示成功，False 表示失败。
    """
    start_time = time.time()

    # === 1. 检测项目类型 ===
    print("[animus]  1/5 检测项目类型 ... ", end="")
    sys.stdout.flush()
    try:
        project_type = detect_project_type(project_root)
        sub_projects = []
        if project_type == "generic":
            sub_projects = detect_sub_projects(project_root)
            if sub_projects:
                names = ", ".join(p[0] for p in sub_projects)
                print("generic (sub: {})".format(names))
            else:
                print(project_type)
        else:
            print(project_type)
    except Exception as e:
        print("FAILED - {}".format(e))
        return False

    # === 2. 准备路径 ===
    state_dir = os.path.join(project_root, ".claude", "animus")
    reports_dir = os.path.join(state_dir, "docs")
    config_path = os.path.join(state_dir, "config.json")
    features_path = os.path.join(state_dir, "features.json")
    lexicon_path = os.path.join(state_dir, "domain-lexicon.md")
    readme_path = os.path.join(state_dir, "README.md")

    # === 3. 创建目录 ===
    print("[animus]  2/5 创建目录结构 ... ", end="")
    sys.stdout.flush()
    try:
        if not _path_exists(state_dir):
            os.makedirs(state_dir)
        if not _path_exists(reports_dir):
            os.makedirs(reports_dir)
    except Exception as e:
        print("FAILED - {}".format(e))
        return False
    print("OK")
    print("[animus]        {}".format(state_dir))

    # === 4. 清理旧 README.md（已废弃） ===
    if _path_exists(readme_path):
        try:
            os.remove(readme_path)
            print("[animus]   Removed obsolete README.md")
        except Exception as e:
            print("[animus]   Warning: could not remove README.md - {}".format(e))

    # === 5. 写入 config.json ===
    print("[animus]  3/5 写入 config.json ... ", end="")
    sys.stdout.flush()
    try:
        if _path_exists(config_path):
            # 已存在 → 跳过，保留现有配置（含注释和所有配置段）
            print("skipped (exists)")
        else:
            new_config = _make_full_toml(project_type, sub_projects)
            _write_json(config_path, new_config)
            print("created")
    except Exception as e:
        print("FAILED - {}".format(e))
        return False

    # === 6. 写入 features.json（如果不存在） ===
    print("[animus]  4/5 写入 features.json ... ", end="")
    sys.stdout.flush()
    try:
        if not _path_exists(features_path):
            now = _now_iso()
            features = {
                "version": 1,
                "tasks": [],
                "created_at": now,
                "updated_at": now,
            }
            _write_json(features_path, features)
            print("created")
        else:
            print("already exists, skipped")
    except Exception as e:
        print("FAILED - {}".format(e))
        return False

    # === 7. 写入 domain-lexicon.md（如果不存在） ===
    if not _path_exists(lexicon_path):
        try:
            lexicon_content = (
                "# 领域术语表（迭代 I1）\n"
                "\n"
                "| 术语 | 英文 | 定义 | 别名 | 来源 |\n"
                "|------|------|------|------|------|\n"
                "\n"
            )
            _write_text(lexicon_path, lexicon_content)
            print("[animus]   Initialized domain-lexicon.md")
        except Exception as e:
            print("[animus]   Warning: could not create domain-lexicon.md - {}".format(e))

    # === 8. 旧状态文件迁移 ===
    print("[animus]  5/5 迁移旧状态文件 ... ", end="")
    sys.stdout.flush()
    old_locations = [
        os.path.join(project_root, ".claude", "harness", "features.json"),
        os.path.join(project_root, ".claude", "state", "features.json"),
    ]
    migrated = False
    for src in old_locations:
        if _path_exists(src):
            dst = os.path.join(state_dir, os.path.basename(src))
            if not _path_exists(dst):
                try:
                    os.renames(src, dst)
                    print("migrated {}".format(os.path.basename(src)))
                    migrated = True
                except Exception as e:
                    print("FAILED {}: {}".format(src, e))
    if not migrated:
        print("none needed")

    # === 9. 完成 ===
    elapsed = time.time() - start_time
    print()
    print("=" * 44)
    print("  animus Setup Complete")
    print("  Project type: {}".format(project_type))
    print("  State dir:    {}".format(state_dir))
    print("  Elapsed:      {:.1f}s".format(elapsed))
    print("=" * 44)
    print()

    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("用法: python animus_init.py [项目根目录]", file=sys.stderr)
        sys.exit(1)

    project_root = os.path.abspath(sys.argv[1])

    if not _path_exists(project_root):
        print("[animus] 错误: 项目目录不存在: {}".format(project_root), file=sys.stderr)
        sys.exit(1)

    success = animus_init(project_root)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
