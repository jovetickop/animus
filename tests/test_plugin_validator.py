#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
"""
plugin-validator 完整测试集 + 文档结构 + 菜单一致性
"""
from __future__ import print_function, unicode_literals
import json
import os
import re
import subprocess
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATOR_PATH = os.path.join(PROJECT_ROOT, "scripts", "plugin-validator.py")
ENGINE_PATH = os.path.join(PROJECT_ROOT, "scripts", "animus-engine.py")


def _read_output(cmd):
    """运行命令并返回输出"""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, _ = proc.communicate()
    try:
        return out.decode("utf-8"), proc.returncode
    except UnicodeDecodeError:
        return out.decode("utf-8", errors="replace"), proc.returncode


class TestPluginValidator(unittest.TestCase):
    """plugin-validator.py 自身测试"""

    def test_validator_runs(self):
        """验证器可正常运行"""
        _, ret = _read_output([sys.executable, VALIDATOR_PATH])
        self.assertIn(ret, (0, 1))

    def test_json_output_structure(self):
        """--json 输出包含必要字段"""
        out, _ = _read_output([sys.executable, VALIDATOR_PATH, "--json"])
        result = json.loads(out)
        self.assertEqual(result.get("version"), "1.0")
        self.assertIn("passed", result)
        self.assertIn("findings", result)
        self.assertIn("errors", result)
        self.assertIn("warnings", result)

    def test_strict_mode(self):
        """--strict 可运行"""
        _, ret = _read_output([sys.executable, VALIDATOR_PATH, "--strict"])
        self.assertIn(ret, (0, 1))

    def test_fix_mode(self):
        """--fix 可运行"""
        _, ret = _read_output([sys.executable, VALIDATOR_PATH, "--fix"])
        self.assertIn(ret, (0, 1))

    def test_engine_integration(self):
        """animus-engine.py validate --plugin 集成"""
        out, ret = _read_output([sys.executable, ENGINE_PATH,
                                 "validate", "--plugin", "--json"])
        self.assertIn(ret, (0, 1))
        try:
            result = json.loads(out)
            self.assertIn("findings", result)
        except (ValueError, KeyError):
            pass


class TestDocsStructure(unittest.TestCase):
    """文档四象限结构完整性测试"""

    def test_quadrant_dirs_exist(self):
        """四个象限目录都存在"""
        for d in ["tutorials", "how-to", "explanation", "reference"]:
            path = os.path.join(PROJECT_ROOT, "docs", d)
            self.assertTrue(os.path.isdir(path),
                            "象限目录缺失: docs/{0}".format(d))

    def test_nav_entry_exists(self):
        """docs/README.md 导航入口存在"""
        path = os.path.join(PROJECT_ROOT, "docs", "README.md")
        self.assertTrue(os.path.isfile(path))

    def test_nav_has_quadrant_table(self):
        """导航页有四象限角色映射表"""
        path = os.path.join(PROJECT_ROOT, "docs", "README.md")
        with open(path, "rb") as f:
            content = f.read().decode("utf-8", errors="replace")
        self.assertIn("Tutorials", content)
        self.assertIn("How-To", content)
        self.assertIn("Explanation", content)
        self.assertIn("Reference", content)
        self.assertIn("tutorials/getting-started", content)

    def test_tutorial_exists(self):
        """上手教程存在"""
        path = os.path.join(PROJECT_ROOT, "docs", "tutorials", "getting-started.md")
        self.assertTrue(os.path.isfile(path))
        with open(path, "rb") as f:
            content = f.read().decode("utf-8", errors="replace")
        self.assertIn("/animus-init", content)

    def test_howto_exists(self):
        """how-to 目录初始文件存在"""
        for name in ["configure-review", "add-new-agent", "customize-hooks"]:
            path = os.path.join(PROJECT_ROOT, "docs", "how-to", name + ".md")
            self.assertTrue(os.path.isfile(path),
                            "how-to 文件缺失: {0}".format(name))

    def test_reference_files_exist(self):
        """reference 目录文件完整"""
        for name in ["commands", "config-options", "testing", "hooks-registry"]:
            path = os.path.join(PROJECT_ROOT, "docs", "reference", name + ".md")
            self.assertTrue(os.path.isfile(path),
                            "reference 文件缺失: {0}".format(name))

    def test_explanation_files_exist(self):
        """explanation 目录文件完整"""
        for name in ["state-machine", "memlog-design"]:
            path = os.path.join(PROJECT_ROOT, "docs", "explanation", name + ".md")
            self.assertTrue(os.path.isfile(path),
                            "explanation 文件缺失: {0}".format(name))

    def test_all_docs_have_frontmatter(self):
        """所有 docs/ 文件有 type frontmatter"""
        for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "docs")):
            for f in files:
                if not f.endswith(".md"):
                    continue
                filepath = os.path.join(root, f)
                with open(filepath, "rb") as fh:
                    content = fh.read().decode("utf-8", errors="replace")
                self.assertIn("type:", content,
                              "缺少 type frontmatter: {0}".format(
                                  os.path.relpath(filepath, PROJECT_ROOT)))

    def test_guide_deprecated(self):
        """guide.md 已标注 deprecated"""
        path = os.path.join(PROJECT_ROOT, "docs", "guide.md")
        with open(path, "rb") as f:
            content = f.read().decode("utf-8", errors="replace")
        self.assertIn("deprecated", content)


class TestAgentMenus(unittest.TestCase):
    """Agent 编号菜单一致性测试"""

    def test_universal_agents_have_menu(self):
        """5 个 universal Agent 有菜单"""
        agents_dir = os.path.join(PROJECT_ROOT, "agents", "universal")
        expected_menus = [
            "task-implementer.md",
            "feature-planner.md",
            "code-reviewer.md",
            "test-engineer.md",
            "build-doctor.md",
        ]
        for name in expected_menus:
            path = os.path.join(agents_dir, name)
            self.assertTrue(os.path.isfile(path),
                            "Agent 文件缺失: universal/{0}".format(name))
            with open(path, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")
            self.assertIn("请选择", content,
                          "universal/{0} 缺少菜单".format(name))

    def test_qt_agents_have_menu(self):
        """Qt Agent 有菜单"""
        qt_dir = os.path.join(PROJECT_ROOT, "agents", "qt")
        for name in ["task-implementer.md", "test-engineer.md", "ui-reviewer.md"]:
            path = os.path.join(qt_dir, name)
            self.assertTrue(os.path.isfile(path),
                            "Agent 文件缺失: qt/{0}".format(name))
            with open(path, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")
            self.assertIn("请选择", content,
                          "qt/{0} 缺少菜单".format(name))

    def test_qt_impl_has_5_items(self):
        """Qt 实现者有 5 项（含 UI 调试）"""
        path = os.path.join(PROJECT_ROOT, "agents", "qt", "task-implementer.md")
        with open(path, "rb") as f:
            content = f.read().decode("utf-8", errors="replace")
        self.assertIn("UI 调试", content)

    def test_lang_test_engineers_have_menu(self):
        """各语言测试官有菜单"""
        for lang in ["python", "node", "rust", "go"]:
            path = os.path.join(PROJECT_ROOT, "agents", lang, "test-engineer.md")
            self.assertTrue(os.path.isfile(path),
                            "Agent 文件缺失: {0}/test-engineer.md".format(lang))
            with open(path, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")
            self.assertIn("请选择", content,
                          "{0}/test-engineer.md 缺少菜单".format(lang))

    def test_menu_uses_numbers(self):
        """菜单使用数字编号 1 2 3 4 而非字母码"""
        agents_dir = os.path.join(PROJECT_ROOT, "agents")
        for root, dirs, files in os.walk(agents_dir):
            for f in files:
                if not f.endswith(".md"):
                    continue
                filepath = os.path.join(root, f)
                with open(filepath, "rb") as fh:
                    content = fh.read().decode("utf-8", errors="replace")
                if "请选择" in content:
                    # 检查使用的是数字编号而非两位字母码
                    lines = content.split("\n")
                    in_menu = False
                    for line in lines:
                        if "请选择" in line:
                            in_menu = True
                            continue
                        if in_menu and line.strip().startswith("---"):
                            break
                        if in_menu and re.match(r"^\s+\d+\.\s", line):
                            pass  # 数字编号正确
                        elif in_menu and re.match(r"^\s+[A-Z]{2}\s", line.strip()):
                            self.fail("{0} 使用了字母码而非数字编号: {1}".format(
                                filepath, line.strip()))


class TestPluginJson(unittest.TestCase):
    """plugin.json 完整性测试"""

    def test_commands_exist(self):
        """plugin.json 中所有命令文件存在"""
        plugin_path = os.path.join(PROJECT_ROOT, ".claude-plugin", "plugin.json")
        with open(plugin_path, "rb") as f:
            data = json.loads(f.read())
        for cmd in data.get("commands", []):
            full = os.path.join(PROJECT_ROOT, cmd)
            self.assertTrue(os.path.isfile(full),
                            "命令文件缺失: {0}".format(cmd))

    def test_version_format(self):
        """版本号符合 semver 格式"""
        plugin_path = os.path.join(PROJECT_ROOT, ".claude-plugin", "plugin.json")
        with open(plugin_path, "rb") as f:
            data = json.loads(f.read())
        version = data.get("version", "")
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
