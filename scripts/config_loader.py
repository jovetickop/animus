#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
两层配置加载器：defaults → config.json
"""

import json
import os
import copy

# ---------- 默认值（硬编码底层） ----------

DEFAULT_CONFIG = {
    "project": {
        "type": "generic",
        "build_command": "",
        "test_command": "",
        "run_command": "",
        "auto_update_plugin": True,
        "verify": {
            "command": "",
            "enabled": False,
            "timeout_seconds": 120,
        },
    },
    "dev": {
        "default_path": "auto",
        "autonomous": False,
    },
    "review": {
        "strictness": "normal",
        "skip_categories": [],
        "max_findings": 20,
    },
    "gates": {
        "require_task_before_write": True,
    },
    "ponytail": {
        "enabled": True,
        "max_lines_per_file": 500,
    },
    "party_mode": {
        "default_mode": "subagent",
        "default_party": "arch-review",
        "auto_trigger": ["dev-full", "review-controversial"],
        "ask_before_start": True,
        "max_rounds": 3,
        "memory_enabled": True,
    },
}


def _try_load_json(path):
    """尝试用 json 加载配置文件，失败返回 None"""
    if not os.path.isfile(path):
        return None

    try:
        with open(path, "rb") as f:
            return json.loads(f.read())
    except Exception:
        return None


def _deep_merge(base, override):
    """
    深度合并两个 dict。override 中的值覆盖 base。
    列表直接替换（不做去重合并）。
    """
    result = copy.deepcopy(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result


def load_config(animus_dir=None):
    """
    加载两层配置，返回合并后的 dict。

    优先级：defaults < config.json
    
    参数：
        animus_dir: .claude/animus/ 目录路径。默认从当前目录查找。
    
    返回：
        合并后的配置 dict
    """
    if animus_dir is None:
        # 从当前目录向上查找 .claude/animus/
        cwd = os.getcwd()
        for _ in range(10):  # 最多向上找 10 层
            candidate = os.path.join(cwd, ".claude", "animus")
            if os.path.isdir(candidate):
                animus_dir = candidate
                break
            parent = os.path.dirname(cwd)
            if parent == cwd:
                break
            cwd = parent

        if animus_dir is None:
            return copy.deepcopy(DEFAULT_CONFIG)

    config = copy.deepcopy(DEFAULT_CONFIG)

    # 加载 config.json（覆盖 defaults）
    team_path = os.path.join(animus_dir, "config.json")
    team_cfg = _try_load_json(team_path)
    if team_cfg:
        config = _deep_merge(config, team_cfg)

    return config


def get_config_value(config, key_path, default=None):
    """
    按点分路径获取配置值。
    
    示例：get_config_value(config, "review.strictness") -> "normal"
    """
    keys = key_path.split(".")
    val = config
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


def get_current_sub_project(config, cwd=None):
    """
    检测当前工作目录是否在某个子项目内。
    
    返回 (sub_dir, project_type) 或 None。
    """
    if cwd is None:
        cwd = os.getcwd()
    cwd = os.path.abspath(cwd)

    sub_projects = get_config_value(config, "project.sub_projects", [])
    if not sub_projects:
        return None

    # 从 cwd 向上查找，匹配最近的子项目
    for sub in sub_projects:
        sub_dir = sub.get("dir", "") if isinstance(sub, dict) else ""
        sub_type = sub.get("type", "") if isinstance(sub, dict) else ""
        if not sub_dir or not sub_type:
            continue
        
        # 精确匹配：检查 sub_dir 是否为 cwd 路径中的完整目录段
        # 避免包含关系的目录名误匹配（如 "frontend" vs "frontend-admin"）
        for i, part in enumerate(cwd.split(os.sep)):
            if part == sub_dir:
                matched_path = os.sep.join(cwd.split(os.sep)[:i+1])
                if os.path.isdir(matched_path):
                    return (sub_dir, sub_type)

    return None


def validate_config(config):
    """
    验证配置的合法性。返回 (is_valid, errors_list)。
    """
    errors = []

    # dev.default_path
    dp = get_config_value(config, "dev.default_path", "")
    if dp not in ("auto", "fast", "light", "full"):
        errors.append("dev.default_path 必须为 auto/fast/light/full")

    # dev.autonomous
    auto = get_config_value(config, "dev.autonomous", None)
    if not isinstance(auto, bool):
        errors.append("dev.autonomous 必须为布尔值")

    # review.strictness
    rs = get_config_value(config, "review.strictness", "")
    if rs not in ("low", "normal", "high"):
        errors.append("review.strictness 必须为 low/normal/high")

    # gates.require_task_before_write
    gate = get_config_value(config, "gates.require_task_before_write", None)
    if not isinstance(gate, bool):
        errors.append("gates.require_task_before_write 必须为布尔值")

    return len(errors) == 0, errors


# ---------- 命令行入口 ----------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        cfg = load_config()
        valid, errors = validate_config(cfg)
        if valid:
            print("config.json 校验通过")
        else:
            print("config.json 校验失败：")
            for e in errors:
                print(f"  - {e}")
        sys.exit(0 if valid else 1)
    else:
        cfg = load_config()
        import json
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
