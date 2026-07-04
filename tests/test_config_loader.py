#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对 scripts/config_loader.py 的单元测试。
使用 pytest 和 tempfile 模拟文件系统，避免依赖真实文件。
"""

import json
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
    get_current_sub_project,
    validate_config,
    _deep_merge,
    _try_load_json,
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
        old_cwd = os.getcwd()
        os.chdir(tmp)
        yield animus
        os.chdir(old_cwd)


def write_config(path, data):
    """将 dict 按 JSON 格式写入 path。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
    """team config.json 覆盖默认值。"""

    def test_team_overrides_dev_path(self, animus_dir):
        """team 覆盖 dev.default_path。"""
        write_config(
            os.path.join(animus_dir, "config.json"),
            {"dev": {"default_path": "fast"}},
        )
        cfg = load_config(animus_dir)
        assert cfg["dev"]["default_path"] == "fast"
        assert cfg["dev"]["autonomous"] is False

    def test_team_overrides_partial(self, animus_dir):
        """team 覆盖部分字段，其余保留默认。"""
        write_config(
            os.path.join(animus_dir, "config.json"),
            {"review": {"strictness": "high", "max_findings": 50}},
        )
        cfg = load_config(animus_dir)
        assert cfg["review"]["strictness"] == "high"
        assert cfg["review"]["max_findings"] == 50
        assert cfg["review"]["skip_categories"] == []

    def test_team_keeps_defaults_for_missing_sections(self, animus_dir):
        """team 只提供部分 section，其余 section 走默认。"""
        write_config(
            os.path.join(animus_dir, "config.json"),
            {"party_mode": {"default_mode": "direct"}},
        )
        cfg = load_config(animus_dir)
        assert cfg["party_mode"]["default_mode"] == "direct"
        assert cfg["party_mode"]["max_rounds"] == 3
        assert cfg["dev"]["default_path"] == "auto"


# ==============================================================
# 3. test_fallback_default
# ==============================================================

class TestFallbackDefault:
    """配置缺失时回退默认值。"""

    def test_team_file_empty(self, animus_dir):
        """配置文件存在但空 -> 完全走默认。"""
        with open(os.path.join(animus_dir, "config.json"), "w") as f:
            f.write("")
        cfg = load_config(animus_dir)
        assert cfg == DEFAULT_CONFIG

    def test_team_file_invalid(self, animus_dir):
        """配置文件内容非法 JSON -> _try_load_json 返回 None -> 走默认。"""
        with open(os.path.join(animus_dir, "config.json"), "w") as f:
            f.write(": invalid json {{{")
        cfg = load_config(animus_dir)
        assert cfg == DEFAULT_CONFIG

    def test_team_section_missing(self, animus_dir):
        """配置缺少某个 section -> 该 section 保留默认。"""
        write_config(
            os.path.join(animus_dir, "config.json"),
            {"ponytail": {"enabled": False}},
        )
        cfg = load_config(animus_dir)
        assert cfg["ponytail"]["enabled"] is False
        assert cfg["gates"]["require_task_before_write"] is True


# ==============================================================
# 4. test_get_config_value
# ==============================================================

class TestGetConfigValue:
    """点分路径取值。"""

    def test_top_level_key(self):
        val = get_config_value(DEFAULT_CONFIG, "dev")
        assert val == DEFAULT_CONFIG["dev"]

    def test_nested_key(self):
        val = get_config_value(DEFAULT_CONFIG, "dev.default_path")
        assert val == "auto"

    def test_deeply_nested_key(self):
        val = get_config_value(DEFAULT_CONFIG, "party_mode.auto_trigger")
        assert val == ["dev-full", "review-controversial"]

    def test_boolean_value(self):
        val = get_config_value(DEFAULT_CONFIG, "gates.require_task_before_write")
        assert val is True

    def test_list_value(self):
        val = get_config_value(DEFAULT_CONFIG, "review.skip_categories")
        assert val == []


# ==============================================================
# 5. test_get_config_value_default
# ==============================================================

class TestGetConfigValueDefault:
    """路径不存在返回 default。"""

    def test_nonexistent_key(self):
        val = get_config_value(DEFAULT_CONFIG, "nonexistent")
        assert val is None

    def test_nonexistent_nested(self):
        val = get_config_value(DEFAULT_CONFIG, "dev.nonexistent")
        assert val is None

    def test_custom_default(self):
        val = get_config_value(DEFAULT_CONFIG, "dev.wrong_key", "fallback")
        assert val == "fallback"

    def test_partial_path(self):
        val = get_config_value(DEFAULT_CONFIG, "dev.default_path.wrong")
        assert val is None

    def test_empty_path(self):
        val = get_config_value(DEFAULT_CONFIG, "")
        assert val is None


# ==============================================================
# 6. test_validate_config_valid
# ==============================================================

class TestValidateConfigValid:
    """合法配置返回 (True, [])。"""

    def test_default_config_is_valid(self):
        valid, errors = validate_config(DEFAULT_CONFIG)
        assert valid is True
        assert errors == []

    def test_all_valid_variants(self):
        for path in ("auto", "fast", "light", "full"):
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            cfg["dev"]["default_path"] = path
            valid, errors = validate_config(cfg)
            assert valid is True, f"path={path} should be valid, got {errors}"

    def test_all_strictness_variants(self):
        for s in ("low", "normal", "high"):
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            cfg["review"]["strictness"] = s
            valid, errors = validate_config(cfg)
            assert valid is True, f"strictness={s} should be valid, got {errors}"

    def test_team_modified_valid_config(self, animus_dir):
        write_config(
            os.path.join(animus_dir, "config.json"),
            {"dev": {"default_path": "light"}, "review": {"strictness": "high"}},
        )
        cfg = load_config(animus_dir)
        valid, errors = validate_config(cfg)
        assert valid is True
        assert errors == []


# ==============================================================
# 7. test_validate_config_invalid
# ==============================================================

class TestValidateConfigInvalid:
    """非法值返回 errors。"""

    def test_invalid_dev_default_path(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["dev"]["default_path"] = "super-fast"
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("dev.default_path" in e for e in errors)

    def test_invalid_dev_autonomous_type(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["dev"]["autonomous"] = "yes"
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("dev.autonomous" in e for e in errors)

    def test_invalid_review_strictness(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["review"]["strictness"] = "extreme"
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("review.strictness" in e for e in errors)

    def test_invalid_gate_type(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["gates"]["require_task_before_write"] = "true"
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("require_task_before_write" in e for e in errors)

    def test_multiple_errors(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["dev"]["default_path"] = "invalid"
        cfg["dev"]["autonomous"] = 123
        cfg["review"]["strictness"] = "invalid"
        cfg["gates"]["require_task_before_write"] = None
        valid, errors = validate_config(cfg)
        assert valid is False
        assert len(errors) >= 4

    def test_missing_section(self):
        cfg = {"dev": {"default_path": "auto", "autonomous": "not_bool"},
               "review": {"strictness": "normal"}}
        valid, errors = validate_config(cfg)
        assert valid is False
        assert any("布尔" in e for e in errors)


# ==============================================================
# 8. _deep_merge 和 _try_load_json 边界
# ==============================================================

class TestDeepMerge:
    """_deep_merge 工具函数行为验证。"""

    def test_list_replaced(self):
        base = {"items": [1, 2]}
        override = {"items": [3, 4, 5]}
        result = _deep_merge(base, override)
        assert result["items"] == [3, 4, 5]

    def test_nested_dict_merge(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 99, "z": 3}}
        result = _deep_merge(base, override)
        assert result["a"]["x"] == 1
        assert result["a"]["y"] == 99
        assert result["a"]["z"] == 3

    def test_new_key_added(self):
        base = {"a": 1}
        override = {"b": 2}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}


class TestTryLoadJson:
    """_try_load_json 边界行为。"""

    def test_file_not_found(self):
        result = _try_load_json("/tmp/__nonexistent_file_for_test__.json")
        assert result is None

    def test_valid_json(self, animus_dir):
        path = os.path.join(animus_dir, "config.json")
        write_config(path, {"dev": {"default_path": "fast"}})
        result = _try_load_json(path)
        assert result == {"dev": {"default_path": "fast"}}


class TestGetCurrentSubProject:
    """测试 get_current_sub_project() 子项目检测"""

    def test_no_sub_projects(self):
        assert get_current_sub_project({"project": {}}) is None

    def test_empty_sub_projects(self):
        cfg = {"project": {"sub_projects": []}}
        assert get_current_sub_project(cfg) is None

    def test_matches_current_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "frontend")
            os.makedirs(sub)
            cfg = {"project": {"sub_projects": [{"dir": "frontend", "type": "node"}]}}
            result = get_current_sub_project(cfg, sub)
            assert result is not None
            assert result[0] == "frontend"

    def test_not_in_sub_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            unrelated = os.path.join(tmp, "other")
            os.makedirs(unrelated)
            cfg = {"project": {"sub_projects": [{"dir": "frontend", "type": "node"}]}}
            result = get_current_sub_project(cfg, unrelated)
            assert result is None

    def test_sub_dir_in_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            deep = os.path.join(tmp, "frontend", "src", "components")
            os.makedirs(deep)
            cfg = {"project": {"sub_projects": [{"dir": "frontend", "type": "node"}]}}
            result = get_current_sub_project(cfg, deep)
            assert result is not None
            assert result[0] == "frontend"

    def test_exact_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "frontend")
            os.makedirs(sub)
            cfg = {"project": {"sub_projects": [
                {"dir": "frontend", "type": "node"},
                {"dir": "frontend-admin", "type": "react"},
            ]}}
            result = get_current_sub_project(cfg, sub)
            assert result is not None
            assert result[0] == "frontend"

    def test_partial_no_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub_admin = os.path.join(tmp, "frontend-admin")
            os.makedirs(sub_admin)
            cfg = {"project": {"sub_projects": [
                {"dir": "frontend", "type": "node"},
                {"dir": "frontend-admin", "type": "react"},
            ]}}
            result = get_current_sub_project(cfg, sub_admin)
            assert result is not None
            assert result[0] == "frontend-admin"
