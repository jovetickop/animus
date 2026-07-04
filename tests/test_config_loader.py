#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对 scripts/config_loader.py 的单元测试。
使用 pytest 和 tempfile 模拟文件系统，避免依赖真实文件。
"""

import os
import sys
import copy
import tempfile

import pytest

# 确保被测试模块可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.config_loader import (
    DEFAULT_CONFIG,
    load_config,
    get_config_value,
    validate_config,
    _deep_merge,
    _try_load_toml,
)


# ==============================================================
# 辅助函数：在临时目录中创建 .claude/animus/ 结构
# ==============================================================

@pytest.fixture
def animus_dir():
    """创建临时 .claude/animus/ 目录，返回路径；清理由 tempfile 自动完成。"""
    with tempfile.TemporaryDirectory() as tmp:
        claude = os.path.join(tmp, ".claude")
        animus = os.path.join(claude, "animus")
        os.makedirs(animus)
        # chdir 进 tmp 以便 load_config() 能找到 .claude/animus/
        old_cwd = os.getcwd()
        os.chdir(tmp)
        yield animus
        os.chdir(old_cwd)


def write_toml(path, data):
    """将 dict 按 TOML 格式写入 path。"""
    _write_toml_file(data, path)


def _write_toml_file(d, path, parent_key=""):
    """简易 TOML 写入器，覆盖嵌套表。"""
    with open(path, "w", encoding="utf-8") as f:
        for key, val in d.items():
            if isinstance(val, dict):
                f.write(f"[{key}]\n")
                for k2, v2 in val.items():
                    _write_toml_value(f, k2, v2)
                f.write("\n")
            else:
                _write_toml_value(f, key, val)


def _write_toml_value(f, key, val):
    """写入单个 TOML key = value 行。"""
    if isinstance(val, bool):
        f.write(f'{key} = {"true" if val else "false"}\n')
    elif isinstance(val, str):
        f.write(f'{key} = "{val}"\n')
    elif isinstance(val, int):
        f.write(f"{key} = {val}\n")
    elif isinstance(val, list):
        items = ", ".join(f'"{v}"' if isinstance(v, str) else str(v).lower() if isinstance(v, bool) else str(v) for v in val)
        f.write(f"{key} = [{items}]\n")
    else:
        f.write(f'{key} = "{val}"\n')


# ==============================================================
# 1. test_default_config
# ==============================================================

class TestDefaultConfig:
    """无配置文件时返回 DEFAULT_CONFIG。"""

    def test_no_animus_dir_returns_default(self):
        """目录不存在 -> 返回 DEFAULT_CONFIG。"""
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                cfg = load_config()
                assert cfg == DEFAULT_CONFIG
            finally:
                os.chdir(old_cwd)

    def test_empty_animus_dir_returns_default(self, animus_dir):
        """目录存在但无任何配置文件 -> 返回 DEFAULT_CONFIG。"""
        cfg = load_config(animus_dir)
        assert cfg == DEFAULT_CONFIG


# ==============================================================
# 2. test_team_config_override
# ==============================================================

class TestTeamConfigOverride:
    """team config.toml 覆盖默认值。"""

    def test_team_overrides_dev_path(self, animus_dir):
        """team 覆盖 dev.default_path。"""
        write_toml(
            os.path.join(animus_dir, "config.toml"),
            {"dev": {"default_path": "fast"}},
        )
        cfg = load_config(animus_dir)
        assert cfg["dev"]["default_path"] == "fast"
        # 未覆盖的 key 保留默认值
        assert cfg["dev"]["autonomous"] is False

    def test_team_overrides_partial(self, animus_dir):
        """team 覆盖部分字段，其余保留默认。"""
        write_toml(
            os.path.join(animus_dir, "config.toml"),
            {"review": {"strictness": "high", "max_findings": 50}},
        )
        cfg = load_config(animus_dir)
        assert cfg["review"]["strictness"] == "high"
        assert cfg["review"]["max_findings"] == 50
        # 默认值保留
        assert cfg["review"]["skip_categories"] == []

    def test_team_keeps_defaults_for_missing_sections(self, animus_dir):
        """team 只提供部分 section，其余 section 走默认。"""
        write_toml(
            os.path.join(animus_dir, "config.toml"),
            {"party_mode": {"default_mode": "direct"}},
        )
        cfg = load_config(animus_dir)
        assert cfg["party_mode"]["default_mode"] == "direct"
        assert cfg["party_mode"]["max_rounds"] == 3  # 默认
        assert cfg["dev"]["default_path"] == "auto"  # 默认


# ==============================================================
# 3. test_user_config_override
# ==============================================================

class TestFallbackDefault:
    """配置缺失时回退默认值（merge 语义已在上面覆盖，这里侧重边界）。"""

    def test_team_file_empty(self, animus_dir):
        """team config.toml 存在但空 -> 完全走默认。"""
        # 写入空文件（仅含注释）
        with open(os.path.join(animus_dir, "config.toml"), "w") as f:
            f.write("# empty\n")
        cfg = load_config(animus_dir)
        assert cfg == DEFAULT_CONFIG

    def test_team_file_invalid_toml(self, animus_dir):
        """team config.toml 内容非法 TOML -> _try_load_toml 返回 None -> 走默认。"""
        with open(os.path.join(animus_dir, "config.toml"), "w") as f:
            f.write(": invalid toml {{{\n")
        cfg = load_config(animus_dir)
        assert cfg == DEFAULT_CONFIG

    def test_user_file_invalid_toml(self, animus_dir):
        """user config.user.toml 非法 -> 忽略 user -> 仅 team + 默认。"""
        write_toml(
            os.path.join(animus_dir, "config.toml"),
            {"dev": {"default_path": "oneshot"}},
        )
        with open(os.path.join(animus_dir, "config.user.toml"), "w") as f:
            f.write("bad data [[[\n")
        cfg = load_config(animus_dir)
        assert cfg["dev"]["default_path"] == "oneshot"

    def test_team_section_missing(self, animus_dir):
        """team 配置缺少某个 section -> 该 section 保留默认。"""
        write_toml(
            os.path.join(animus_dir, "config.toml"),
            {"ponytail": {"enabled": False}},
        )
        cfg = load_config(animus_dir)
        # ponytail 被覆盖
        assert cfg["ponytail"]["enabled"] is False
        # gates 完全走默认
        assert cfg["gates"]["require_task_before_write"] is True


# ==============================================================
# 5. test_get_config_value
# ==============================================================

class TestGetConfigValue:
    """点分路径取值。"""

    def test_top_level_key(self):
        """一级 key。"""
        val = get_config_value(DEFAULT_CONFIG, "dev")
        assert val == DEFAULT_CONFIG["dev"]

    def test_nested_key(self):
        """嵌套 key。"""
        val = get_config_value(DEFAULT_CONFIG, "dev.default_path")
        assert val == "auto"

    def test_deeply_nested_key(self):
        """多层嵌套。"""
        val = get_config_value(DEFAULT_CONFIG, "party_mode.auto_trigger")
        assert val == ["dev-full", "review-controversial"]

    def test_boolean_value(self):
        """布尔值。"""
        val = get_config_value(DEFAULT_CONFIG, "gates.require_task_before_write")
        assert val is True

    def test_list_value(self):
        """列表值。"""
        val = get_config_value(DEFAULT_CONFIG, "review.skip_categories")
        assert val == []


# ==============================================================
# 6. test_get_config_value_default
# ==============================================================

class TestGetConfigValueDefault:
    """路径不存在返回 default。"""

    def test_nonexistent_key(self):
        """不存在的 key。"""
        val = get_config_value(DEFAULT_CONFIG, "nonexistent")
        assert val is None

    def test_nonexistent_nested(self):
        """不存在的嵌套路径。"""
        val = get_config_value(DEFAULT_CONFIG, "dev.nonexistent")
        assert val is None

    def test_custom_default(self):
        """自定义 default 值。"""
        val = get_config_value(DEFAULT_CONFIG, "dev.wrong_key", "fallback")
        assert val == "fallback"

    def test_partial_path(self):
        """部分路径无效。"""
        val = get_config_value(DEFAULT_CONFIG, "dev.default_path.wrong")
        assert val is None  # "auto" 不是 dict，继续走 k 会失败

    def test_empty_path(self):
        """空路径。"""
        val = get_config_value(DEFAULT_CONFIG, "")
        assert val is None  # 空字符串 split 为 [""]，不存在


# ==============================================================
# 7. test_validate_config_valid
# ==============================================================

class TestValidateConfigValid:
    """合法配置返回 (True, [])。"""

    def test_default_config_is_valid(self):
        """DEFAULT_CONFIG 本身就是合法的。"""
        valid, errors = validate_config(DEFAULT_CONFIG)
        assert valid is True
        assert errors == []

    def test_all_valid_variants(self):
        """dev.default_path 每个合法值都应通过。"""
        for path in ("auto", "fast", "light", "full", "oneshot"):
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            cfg["dev"]["default_path"] = path
            valid, errors = validate_config(cfg)
            assert valid is True, f"path={path} should be valid, got {errors}"

    def test_all_strictness_variants(self):
        """review.strictness 每个合法值都应通过。"""
        for s in ("low", "normal", "high"):
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            cfg["review"]["strictness"] = s
            valid, errors = validate_config(cfg)
            assert valid is True, f"strictness={s} should be valid, got {errors}"

    def test_team_modified_valid_config(self, animus_dir):
        """通过 team 配置产生的合法修改也应通过校验。"""
        write_toml(
            os.path.join(animus_dir, "config.toml"),
            {"dev": {"default_path": "light"}, "review": {"strictness": "high"}},
        )
        cfg = load_config(animus_dir)
        valid, errors = validate_config(cfg)
        assert valid is True
        assert errors == []


# ==============================================================
# 8. test_validate_config_invalid
# ==============================================================

class TestValidateConfigInvalid:
    """非法值返回 errors。"""

    def test_invalid_dev_default_path(self):
        """dev.default_path 为非法值。"""
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["dev"]["default_path"] = "super-fast"
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("dev.default_path" in e for e in errors)

    def test_invalid_dev_autonomous_type(self):
        """dev.autonomous 非布尔值。"""
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["dev"]["autonomous"] = "yes"
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("dev.autonomous" in e for e in errors)

    def test_invalid_review_strictness(self):
        """review.strictness 非法。"""
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["review"]["strictness"] = "extreme"
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("review.strictness" in e for e in errors)

    def test_invalid_gate_type(self):
        """gates.require_task_before_write 非布尔值。"""
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["gates"]["require_task_before_write"] = "true"
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("require_task_before_write" in e for e in errors)

    def test_multiple_errors(self):
        """多个字段同时非法 -> 多个 errors。"""
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["dev"]["default_path"] = "invalid"
        cfg["dev"]["autonomous"] = 123
        cfg["review"]["strictness"] = "invalid"
        cfg["gates"]["require_task_before_write"] = None
        valid, errors = validate_config(cfg)
        assert valid is False
        assert len(errors) >= 4

    def test_missing_section(self):
        """缺少整个 section 时 get_config_value 返回 default -> 触发校验错误。"""
        cfg = {
            "dev": {"default_path": "auto", "autonomous": "not_bool"},
            "review": {"strictness": "normal"},
        }
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("布尔" in e for e in errors)


# ==============================================================
# 额外：_deep_merge 和 _try_load_toml 边界
# ==============================================================

class TestDeepMerge:
    """_deep_merge 工具函数行为验证。"""

    def test_list_replaced(self):
        """列表直接替换（非合并）。"""
        base = {"items": [1, 2]}
        override = {"items": [3, 4, 5]}
        result = _deep_merge(base, override)
        assert result["items"] == [3, 4, 5]

    def test_nested_dict_merge(self):
        """嵌套 dict 合并。"""
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 99, "z": 3}}
        result = _deep_merge(base, override)
        assert result["a"]["x"] == 1  # 保留
        assert result["a"]["y"] == 99  # 覆盖
        assert result["a"]["z"] == 3  # 新增

    def test_new_key_added(self):
        """override 新增顶级 key。"""
        base = {"a": 1}
        override = {"b": 2}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}


class TestTryLoadToml:
    """_try_load_toml 边界行为。"""

    def test_file_not_found(self):
        """文件不存在返回 None。"""
        result = _try_load_toml("/tmp/__nonexistent_file_for_test__.toml")
        assert result is None

    def test_valid_toml(self, animus_dir):
        """合法 TOML 文件返回解析后的 dict。"""
        path = os.path.join(animus_dir, "config.toml")
        write_toml(path, {"dev": {"default_path": "fast"}})
        result = _try_load_toml(path)
        assert result == {"dev": {"default_path": "fast"}}
