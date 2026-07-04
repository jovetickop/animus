#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三层配置加载器：defaults → team config.toml → user config.user.toml
兼容 Python 3.11+（使用标准库 tomllib）和 Python 3.9-3.10（使用 tomli 或回退）。
"""

import os
import copy

# ---------- 默认值（硬编码底层） ----------

DEFAULT_CONFIG = {
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


def _try_load_toml(path):
    """尝试用可用的 TOML 解析器加载文件，失败返回 None"""
    if not os.path.isfile(path):
        return None

    # Python 3.11+：标准库
    try:
        import tomllib
        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        pass
    except Exception:
        return None

    # Python 3.9-3.10：第三方 tomli
    try:
        import tomli
        with open(path, "rb") as f:
            return tomli.load(f)
    except ImportError:
        pass
    except Exception:
        return None

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
    加载三层配置，返回合并后的 dict。
    
    优先级：defaults < team config.toml < user config.user.toml
    
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

    # Team 层：config.toml（git 跟踪）
    team_path = os.path.join(animus_dir, "config.toml")
    team_cfg = _try_load_toml(team_path)
    if team_cfg:
        config = _deep_merge(config, team_cfg)

    # User 层：config.user.toml（gitignored）
    user_path = os.path.join(animus_dir, "config.user.toml")
    user_cfg = _try_load_toml(user_path)
    if user_cfg:
        config = _deep_merge(config, user_cfg)

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


def validate_config(config):
    """
    验证配置的合法性。返回 (is_valid, errors_list)。
    """
    errors = []

    # dev.default_path
    dp = get_config_value(config, "dev.default_path", "")
    if dp not in ("auto", "fast", "light", "full", "oneshot"):
        errors.append("dev.default_path 必须为 auto/fast/light/full/oneshot")

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
            print("config.toml 校验通过")
        else:
            print("config.toml 校验失败：")
            for e in errors:
                print(f"  - {e}")
        sys.exit(0 if valid else 1)
    else:
        cfg = load_config()
        import json
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
