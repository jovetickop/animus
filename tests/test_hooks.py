#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对 hooks/scripts/ 下 5 个钩子脚本的单元测试。

测试范围：
  - write-gate.py   门控检查（是否有 in_progress 任务）
  - pre-tool-use.py 备份与门控集成
  - pre-compact.py  状态概览输出
  - stop-check.py   未完成任务检测
  - clang-format.py GBK 编码检查

使用 pytest + tempfile 模拟文件系统，不依赖真实项目目录。
每个测试独立执行，互不依赖。
"""

from __future__ import print_function, unicode_literals

import json
import os
import sys
import tempfile

import pytest

# ---------------------------------------------------------------------------
# 将被测模块所在目录加入 sys.path，以便 import
# ---------------------------------------------------------------------------
_HOOKS_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "hooks", "scripts")
_HOOKS_DIR = os.path.normpath(os.path.abspath(_HOOKS_DIR))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)


def _load_module(name, filename):
    """
    从 hooks/scripts/ 目录加载 Python 模块。
    兼容 Python 2/3，文件名中有连字符也可加载。
    """
    path = os.path.join(_HOOKS_DIR, filename)
    if sys.version_info[0] < 3:
        import imp
        return imp.load_source(name, path)
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


# ---------------------------------------------------------------------------
# fixtures 共用
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_animus():
    """创建临时 .claude/animus/ 目录，返回 (tmpdir, animus_dir) 元组。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        animus = os.path.join(tmpdir, ".claude", "animus")
        os.makedirs(animus)
        yield tmpdir, animus


def _write_features(animus_dir, data):
    """将 data (dict) 写入 animus_dir/features.json。"""
    path = os.path.join(animus_dir, "features.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _write_config(animus_dir, content):
    """将 content (str) 写入 animus_dir/config.toml。"""
    path = os.path.join(animus_dir, "config.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _run_main(mod, argv, cwd=None):
    """
    在给定 argv 下运行模块的 main()，捕获 SystemExit。
    返回 (exit_code, stdout_text)。
    注意：此函数会修改 sys.argv / sys.stdout，调用者需确保串行使用。
    """
    import io
    old_argv = sys.argv[:]
    old_stdout = sys.stdout
    old_cwd = os.getcwd()
    sys.argv = argv[:]
    buf = io.StringIO()
    sys.stdout = buf
    try:
        if cwd:
            os.chdir(cwd)
        try:
            mod.main()
            code = 0
        except SystemExit as e:
            code = e.code if e.code is not None else 0
        return code, buf.getvalue()
    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
        if cwd:
            os.chdir(old_cwd)


# ===================================================================
# write-gate.py 测试
# ===================================================================

class TestWriteGate(object):
    """write-gate.py：门控检查，测试 has_in_progress_tasks 及 CLI main()。"""

    def _mod(self):
        """延迟加载 write-gate 模块"""
        return _load_module("write_gate", "write-gate.py")

    def test_no_features_json(self, tmp_animus):
        """features.json 不存在 → exit 0（失败安全放行）"""
        mod = self._mod()
        tmpdir, _ = tmp_animus
        code, _ = _run_main(mod, ["write-gate.py", tmpdir])
        assert code == 0, "features.json 不存在时应放行 (exit 0)"

    def test_empty_tasks(self, tmp_animus):
        """空 tasks 列表 → exit 1 并输出阻塞提示"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_features(animus_dir, {"tasks": []})
        code, out = _run_main(mod, ["write-gate.py", tmpdir])
        assert code == 1, "空 tasks 列表时应阻塞 (exit 1)"
        assert "阻塞" in out or "Blocked" in out, "应输出阻塞提示信息"

    def test_has_in_progress(self, tmp_animus):
        """有 in_progress 任务 → exit 0（放行）"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_features(animus_dir, {
            "tasks": [
                {"id": "T001", "status": "in_progress", "name": u"进行中"}
            ]
        })
        code, _ = _run_main(mod, ["write-gate.py", tmpdir])
        assert code == 0, "有 in_progress 任务时应放行 (exit 0)"

    def test_all_pending(self, tmp_animus):
        """只有 pending 任务 → exit 1（阻塞）"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_features(animus_dir, {
            "tasks": [
                {"id": "T001", "status": "pending", "name": u"待办"},
                {"id": "T002", "status": "pending", "name": u"待办2"}
            ]
        })
        code, out = _run_main(mod, ["write-gate.py", tmpdir])
        assert code == 1, "只有 pending 任务时应阻塞 (exit 1)"
        assert "阻塞" in out or "Blocked" in out, "应输出阻塞提示信息"

    def test_invalid_json(self, tmp_animus):
        """features.json 格式错误 → exit 0（失败安全放行）"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        bad_path = os.path.join(animus_dir, "features.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("{invalid json,}")
        code, _ = _run_main(mod, ["write-gate.py", tmpdir])
        assert code == 0, "JSON 格式错误时应失败安全放行 (exit 0)"

    def test_has_in_progress_tasks_func(self, tmp_animus):
        """直接测试 has_in_progress_tasks 函数逻辑"""
        mod = self._mod()
        # dict 格式的 tasks
        assert mod.has_in_progress_tasks(
            {"tasks": {"T001": {"status": "in_progress"}}}
        ) is True
        # list 格式的 tasks
        assert mod.has_in_progress_tasks(
            {"tasks": [{"status": "in_progress"}]}
        ) is True
        # 无 in_progress
        assert mod.has_in_progress_tasks(
            {"tasks": [{"status": "pending"}]}
        ) is False
        # 空 tasks
        assert mod.has_in_progress_tasks({"tasks": []}) is False
        # 无 tasks 键
        assert mod.has_in_progress_tasks({}) is False


# ===================================================================
# pre-tool-use.py 测试
# ===================================================================

class TestPreToolUse(object):
    """pre-tool-use.py：备份与门控集成。"""

    def _mod(self):
        return _load_module("pre_tool_use", "pre-tool-use.py")

    def test_backup_features(self, tmp_animus):
        """备份 features.json 到 .features.backup.json"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        features = {"tasks": [{"id": "T001", "status": "in_progress"}]}
        _write_features(animus_dir, features)

        from unittest.mock import patch
        # 直接 patch 模块内的 subprocess.call 属性，避免字符串 import 问题
        with patch.object(mod.subprocess, "call", return_value=0):
            code, out = _run_main(mod, ["pre-tool-use.py", tmpdir])

        assert code == 0, u"门控放行时 pre-tool-use 应 exit 0"
        backup_path = os.path.join(animus_dir, ".features.backup.json")
        assert os.path.isfile(backup_path), u"应创建 .features.backup.json"
        with open(backup_path, "r", encoding="utf-8") as f:
            assert json.load(f) == features, u"备份内容应与原文件一致"

    def test_backup_no_features(self, tmp_animus):
        """features.json 不存在时不报错，静默继续"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        from unittest.mock import patch
        with patch.object(mod.subprocess, "call", return_value=0):
            code, out = _run_main(mod, ["pre-tool-use.py", tmpdir])
        assert code == 0, u"features.json 不存在时应静默继续 (exit 0)"
        # 不应产生备份文件
        backup_path = os.path.join(animus_dir, ".features.backup.json")
        assert not os.path.isfile(backup_path), "不应创建备份文件"

    def test_write_gate_blocks(self, tmp_animus):
        """write-gate exit 1 时 pre-tool-use 也 exit 1"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_features(animus_dir, {"tasks": [{"status": "pending"}]})
        from unittest.mock import patch
        with patch.object(mod.subprocess, "call", return_value=1):
            code, out = _run_main(mod, ["pre-tool-use.py", tmpdir])
        assert code == 1, u"write-gate 阻塞时 pre-tool-use 也应 exit 1"


# ===================================================================
# pre-compact.py 测试
# ===================================================================

class TestPreCompact(object):
    """pre-compact.py：状态概览输出与失败安全。"""

    def _mod(self):
        return _load_module("pre_compact", "pre-compact.py")

    def test_output_format(self, tmp_animus):
        """读取有效 features.json，输出 X/Y 任务完成统计"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_features(animus_dir, {
            "tasks": [
                {"id": "T001", "status": "passed"},
                {"id": "T002", "status": "in_progress"},
                {"id": "T003", "status": "pending"},
            ]
        })
        code, out = _run_main(mod, ["pre-compact.py", tmpdir])
        assert code == 0, "pre-compact 应始终 exit 0"
        assert "任务完成" in out or "PreCompact" in out or "1/3" in out, \
            "输出应包含任务完成统计信息"

    def test_no_features(self, tmp_animus):
        """features.json 不存在时不报错，静默 exit 0"""
        mod = self._mod()
        tmpdir, _ = tmp_animus
        code, out = _run_main(mod, ["pre-compact.py", tmpdir])
        assert code == 0, "features.json 不存在时应静默 exit 0"

    def test_count_statuses(self, tmp_animus):
        """直接测试 count_statuses 函数"""
        mod = self._mod()
        tasks = [
            {"status": "passed"},
            {"status": "passed"},
            {"status": "in_progress"},
            {"status": "pending"},
        ]
        counts = mod.count_statuses(tasks)
        assert counts.get("passed") == 2
        assert counts.get("in_progress") == 1
        assert counts.get("pending") == 1

    def test_extract_tasks_list(self, tmp_animus):
        """直接测试 extract_tasks：列表格式"""
        mod = self._mod()
        data = [{"id": "T001"}, {"id": "T002"}]
        assert mod.extract_tasks(data) == data

    def test_extract_tasks_dict_with_tasks(self, tmp_animus):
        """直接测试 extract_tasks：字典含 tasks 列表"""
        mod = self._mod()
        tasks = [{"id": "T001"}, {"id": "T002"}]
        data = {"tasks": tasks}
        assert mod.extract_tasks(data) == tasks

    def test_extract_tasks_dict_initial(self, tmp_animus):
        """直接测试 extract_tasks：字典含 initial_tasks"""
        mod = self._mod()
        tasks = [{"id": "T001"}]
        data = {"initial_tasks": tasks}
        assert mod.extract_tasks(data) == tasks

    def test_extract_tasks_empty(self, tmp_animus):
        """直接测试 extract_tasks：无任务时返回空列表"""
        mod = self._mod()
        assert mod.extract_tasks({}) == []


# ===================================================================
# stop-check.py 测试
# ===================================================================

class TestStopCheck(object):
    """stop-check.py：会话结束时的任务状态检查。"""

    def _mod(self):
        return _load_module("stop_check", "stop-check.py")

    def _call_main(self, mod, tmpdir, animus_dir):
        """
        运行 stop_check.main()，通过环境变量指定项目根目录
        （因为 stop-check.py 使用 find_project_root() 而非 sys.argv）
        """
        import io
        old_env = os.environ.get("CLAUDE_PROJECT_ROOT")
        old_argv = sys.argv[:]
        old_stdout = sys.stdout
        os.environ["CLAUDE_PROJECT_ROOT"] = tmpdir
        sys.argv = ["stop-check.py"]
        buf = io.StringIO()
        sys.stdout = buf
        try:
            try:
                mod.main()
                code = 0
            except SystemExit as e:
                code = e.code if e.code is not None else 0
            return code, buf.getvalue()
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout
            if old_env is None:
                os.environ.pop("CLAUDE_PROJECT_ROOT", None)
            else:
                os.environ["CLAUDE_PROJECT_ROOT"] = old_env

    def test_no_incomplete(self, tmp_animus):
        """所有任务已完成 → 不输出恢复提示，静默 exit 0"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_features(animus_dir, {
            "tasks": [
                {"id": "T001", "status": "passed", "name": u"完成1"},
                {"id": "T002", "status": "completed", "name": u"完成2"},
            ]
        })
        code, out = self._call_main(mod, tmpdir, animus_dir)
        assert code == 0, "所有任务已完成时应 exit 0"
        assert u"恢复建议" not in out, u"不应输出恢复建议"
        assert u"正在进行" not in out, u"不应输出进行中提示"

    def test_has_incomplete(self, tmp_animus):
        """有 in_progress 任务 → 输出恢复建议"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_features(animus_dir, {
            "tasks": [
                {"id": "T001", "status": "in_progress", "name": u"进行中"},
                {"id": "T002", "status": "pending", "name": u"待办"},
            ]
        })
        code, out = self._call_main(mod, tmpdir, animus_dir)
        assert code == 0, "stop-check 应始终 exit 0"
        assert u"恢复建议" in out or u"进行中" in out or u"任务状态检查" in out, \
            u"应输出恢复建议或任务状态信息"

    def test_no_features(self, tmp_animus):
        """features.json 不存在时不报错"""
        mod = self._mod()
        tmpdir, _ = tmp_animus
        code, out = self._call_main(mod, tmpdir, tmpdir)
        assert code == 0, "features.json 不存在时应静默 exit 0"
        assert out == "", u"不应有任何输出"

    def test_get_tasks(self, tmp_animus):
        """直接测试 get_tasks 函数"""
        mod = self._mod()
        assert mod.get_tasks([1, 2]) == [1, 2]
        assert mod.get_tasks({"tasks": [1]}) == [1]
        assert mod.get_tasks({"initial_tasks": [1]}) == [1]
        assert mod.get_tasks({}) == []


# ===================================================================
# clang-format.py 测试
# ===================================================================

class TestClangFormat(object):
    """clang-format.py：GBK 编码检查逻辑。"""

    def _mod(self):
        return _load_module("clang_format", "clang-format.py")

    def test_config_gbk(self, tmp_animus):
        """config.toml 含 encoding=gbk → check_gbk_encoding 返回 True"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_config(animus_dir, "encoding=gbk\n")
        assert mod.check_gbk_encoding(tmpdir) is True, \
            "config.toml 含 encoding=gbk 时应返回 True"

    def test_config_gbk_quoted(self, tmp_animus):
        """config.toml 含 encoding = "gbk" → 返回 True"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_config(animus_dir, 'encoding = "gbk"\n')
        assert mod.check_gbk_encoding(tmpdir) is True, \
            'config.toml 含 encoding = "gbk" 时应返回 True'

    def test_config_no_gbk(self, tmp_animus):
        """config.toml 不含 gbk → check_gbk_encoding 返回 False"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_config(animus_dir, "encoding=utf-8\n")
        assert mod.check_gbk_encoding(tmpdir) is False, \
            "config.toml 不含 gbk 时应返回 False"

    def test_config_no_file(self, tmp_animus):
        """config.toml 不存在 → check_gbk_encoding 返回 False"""
        mod = self._mod()
        tmpdir, _ = tmp_animus
        assert mod.check_gbk_encoding(tmpdir) is False, \
            "config.toml 不存在时应返回 False"

    def test_config_empty(self, tmp_animus):
        """config.toml 为空文件 → 返回 False"""
        mod = self._mod()
        tmpdir, animus_dir = tmp_animus
        _write_config(animus_dir, "")
        assert mod.check_gbk_encoding(tmpdir) is False, \
            "空 config.toml 应返回 False"

    def test_c_extensions(self, tmp_animus):
        """验证 C_EXTENSIONS 常量包含预期的扩展名"""
        mod = self._mod()
        for ext in ('.cpp', '.c', '.h', '.hpp', '.cc', '.cxx', '.hxx'):
            assert ext in mod.C_EXTENSIONS, \
                u"缺少扩展名: {0}".format(ext)
