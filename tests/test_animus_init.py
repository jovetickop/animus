#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_animus_init.py — 对 scripts/animus_init.py 和 templates/init_project.py 做单元测试

Python 2/3 兼容。
"""

from __future__ import print_function, unicode_literals

import json
import os
import sys
import tempfile
import unittest

# 将项目根目录加入 sys.path，以便导入被测模块
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ======================================================================
# 测试: scripts/animus_init.py
# ======================================================================

class TestAnimusInitDetectProjectType(unittest.TestCase):
    """检测项目类型 — detect_project_type"""

    def setUp(self):
        """每个测试前创建临时目录。"""
        self.tmpdir = tempfile.mkdtemp(prefix="animus_test_")

    def tearDown(self):
        """每个测试后清理临时目录。"""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _import_module(self):
        """动态导入 animus_init（清除缓存以确保重新加载）。"""
        key = "scripts.animus_init"
        for k in list(sys.modules.keys()):
            if k.endswith("animus_init"):
                del sys.modules[k]
        sys.path.insert(0, _PROJECT_ROOT)
        import scripts.animus_init as m
        return m

    # ------------------------------------------------------------------
    # detect_project_type 测试
    # ------------------------------------------------------------------

    def test_detect_project_type_cpp_qt(self):
        """创建 CMakeLists.txt（含 Qt）→ 返回 cpp-qt"""
        cmake_content = (
            "cmake_minimum_required(VERSION 3.16)\n"
            "project(MyApp)\n"
            "find_package(Qt6 COMPONENTS Core Gui Widgets REQUIRED)\n"
            "add_executable(myapp main.cpp)\n"
        )
        with open(os.path.join(self.tmpdir, "CMakeLists.txt"), "w") as f:
            f.write(cmake_content)

        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "cpp-qt")

    def test_detect_project_type_cpp_cmake(self):
        """创建 CMakeLists.txt（不含 Qt）→ 返回 cpp-cmake"""
        cmake_content = (
            "cmake_minimum_required(VERSION 3.16)\n"
            "project(MyApp)\n"
            "add_executable(myapp main.cpp)\n"
        )
        with open(os.path.join(self.tmpdir, "CMakeLists.txt"), "w") as f:
            f.write(cmake_content)

        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "cpp-cmake")

    def test_detect_project_type_rust(self):
        """创建 Cargo.toml → 返回 rust"""
        with open(os.path.join(self.tmpdir, "Cargo.toml"), "w") as f:
            f.write('[package]\nname = "myapp"\n')

        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "rust")

    def test_detect_project_type_go(self):
        """创建 go.mod → 返回 go"""
        with open(os.path.join(self.tmpdir, "go.mod"), "w") as f:
            f.write("module myapp\n")

        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "go")

    def test_detect_project_type_node(self):
        """创建 package.json → 返回 node"""
        with open(os.path.join(self.tmpdir, "package.json"), "w") as f:
            json.dump({"name": "myapp"}, f)

        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "node")

    def test_detect_project_type_python(self):
        """创建 pyproject.toml → 返回 python"""
        with open(os.path.join(self.tmpdir, "pyproject.toml"), "w") as f:
            f.write('[build-system]\nrequires = ["setuptools"]\n')

        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "python")

    def test_detect_project_type_generic(self):
        """无匹配文件 → 返回 generic"""
        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "generic")


class TestAnimusInitMakeFullToml(unittest.TestCase):
    """测试 _make_full_toml"""

    def test_make_full_toml(self):
        """生成的 TOML 包含 [project] 段"""
        import scripts.animus_init as mod
        result = mod._make_full_toml("cpp-qt")
        self.assertIn("project", result)
        self.assertEqual(result["project"]["type"], "cpp-qt")
        self.assertIn("build_command", result["project"])
        self.assertIn("test_command", result["project"])


class TestAnimusInitProject(unittest.TestCase):
    """测试 animus_init 主流程"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="animus_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _import_module(self):
        key = "scripts.animus_init"
        for k in list(sys.modules.keys()):
            if k.endswith("animus_init"):
                del sys.modules[k]
        sys.path.insert(0, _PROJECT_ROOT)
        import scripts.animus_init as m
        return m

    def test_init_project_creates_dirs(self):
        """animus_init 应创建 .claude/animus/ 目录"""
        mod = self._import_module()
        result = mod.animus_init(self.tmpdir)
        self.assertTrue(result)
        state_dir = os.path.join(self.tmpdir, ".claude", "animus")
        self.assertTrue(os.path.isdir(state_dir))
        reports_dir = os.path.join(state_dir, "docs")
        self.assertTrue(os.path.isdir(reports_dir))

    def test_init_project_creates_features(self):
        """animus_init 应创建 features.json"""
        mod = self._import_module()
        result = mod.animus_init(self.tmpdir)
        self.assertTrue(result)
        features_path = os.path.join(self.tmpdir, ".claude", "animus", "features.json")
        self.assertTrue(os.path.isfile(features_path))
        data = json.load(open(features_path))
        self.assertIn("version", data)
        self.assertIn("tasks", data)

    def test_init_project_creates_config_toml(self):
        """animus_init 应创建 config.toml"""
        mod = self._import_module()
        result = mod.animus_init(self.tmpdir)
        self.assertTrue(result)
        config_path = os.path.join(self.tmpdir, ".claude", "animus", "config.toml")
        self.assertTrue(os.path.isfile(config_path))

    def test_init_project_skip_existing(self):
        """已存在时不覆盖"""
        mod = self._import_module()
        # 第一次初始化
        mod.animus_init(self.tmpdir)
        features_path = os.path.join(self.tmpdir, ".claude", "animus", "features.json")
        # 修改 features.json
        with open(features_path, "w") as f:
            json.dump({"modified": True}, f)
        # 第二次初始化
        mod.animus_init(self.tmpdir)
        # 验证未被覆盖
        data = json.load(open(features_path))
        self.assertIn("modified", data)
        self.assertTrue(data["modified"])


# ======================================================================
# 测试: templates/init_project.py
# ======================================================================

class TestInitProjectTemplate(unittest.TestCase):
    """测试 templates/init_project.py 的目录创建和 README 写入"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="animus_init_template_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _import_module(self):
        key = "templates.init_project"
        for k in list(sys.modules.keys()):
            if k.endswith("init_project"):
                del sys.modules[k]
        sys.path.insert(0, _PROJECT_ROOT)
        import templates.init_project as m
        return m

    def test_create_structure(self):
        """创建目标目录结构"""
        mod = self._import_module()
        state_dir = os.path.join(self.tmpdir, ".claude", "animus")
        reports_dir = os.path.join(state_dir, "docs")

        mod._ensure_dir(state_dir)
        mod._ensure_dir(reports_dir)

        self.assertTrue(os.path.isdir(state_dir))
        self.assertTrue(os.path.isdir(reports_dir))

    def test_write_readme(self):
        """写入 README.md"""
        mod = self._import_module()
        state_dir = os.path.join(self.tmpdir, ".claude", "animus")
        mod._ensure_dir(state_dir)

        readme_path = os.path.join(state_dir, "README.md")
        content = "# animus\n\nTest project.\n"
        mod._write_file(readme_path, content)

        self.assertTrue(os.path.isfile(readme_path))
        with open(readme_path, "rb") as f:
            written = f.read().decode("utf-8")
        self.assertIn("animus", written)
        self.assertIn("Test project.", written)

    def test_detect_project_type_cpp_qt(self):
        """模板中的 detect_project_type 检测 cpp-qt"""
        cmake_content = (
            "cmake_minimum_required(VERSION 3.16)\n"
            "find_package(Qt6 COMPONENTS Core REQUIRED)\n"
        )
        with open(os.path.join(self.tmpdir, "CMakeLists.txt"), "w") as f:
            f.write(cmake_content)

        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "cpp-qt")

    def test_detect_project_type_python(self):
        """模板中的 detect_project_type 检测 python（requirements.txt）"""
        with open(os.path.join(self.tmpdir, "requirements.txt"), "w") as f:
            f.write("requests\n")

        mod = self._import_module()
        result = mod.detect_project_type(self.tmpdir)
        self.assertEqual(result, "python")


if __name__ == "__main__":
    unittest.main()
