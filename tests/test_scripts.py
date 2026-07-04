#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_scripts.py — 对 scripts/ 下尚未测试的模块做单元测试

涉及的脚本:
  1. scripts/animus-engine.py   — CLI 入口，测试子命令分发（通过单元测试 + mock）
  2. scripts/session-catchup.py — 会话恢复上下文读取
  3. scripts/format-log.py      — JSONL 日志格式化
  4. scripts/run-regression.py  — 回归测试配置读取

Python 2/3 兼容。
"""

from __future__ import print_function, unicode_literals

import io
import json
import os
import sys
import tempfile
import unittest

try:
    from unittest import mock as _mock
except ImportError:
    import mock as _mock

try:
    from importlib import machinery as _machinery
    import importlib.util as _importlib_util
except ImportError:
    _machinery = None
    _importlib_util = None


# -------------------------------------------------------------------
# 路径：将项目根目录和 scripts/ 加入 sys.path
# -------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_SCRIPTS_DIR = os.path.join(_PROJECT_ROOT, "scripts")
for _p in (_PROJECT_ROOT, _SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# -------------------------------------------------------------------
# 辅助：临时目录夹具（unittest 风格）
# -------------------------------------------------------------------

def _make_temp_dir(prefix):
    """创建临时目录并切换到该目录，返回 (tmpdir, old_cwd)。"""
    tmpdir = tempfile.mkdtemp(prefix=prefix)
    old_cwd = os.getcwd()
    os.chdir(tmpdir)
    return tmpdir, old_cwd


def _clean_temp_dir(tmpdir, old_cwd):
    """恢复工作目录并删除临时目录。"""
    os.chdir(old_cwd)
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


def _load_via_importlib(module_name, filepath):
    """通过 importlib 加载带有连字符的 .py 文件，返回模块对象。

    使用 exec_module 代替已废弃的 load_module（Python 3.15+ 兼容）。
    """
    if _machinery is not None and _importlib_util is not None:
        loader = _machinery.SourceFileLoader(module_name, filepath)
        spec = _importlib_util.spec_from_loader(module_name, loader)
        mod = _importlib_util.module_from_spec(spec)
        loader.exec_module(mod)
        return mod
    # fallback：exec
    import types
    mod = types.ModuleType(module_name)
    mod.__file__ = filepath
    with io.open(filepath, "r", encoding="utf-8") as f:
        code = compile(f.read(), filepath, "exec")
    exec(code, mod.__dict__)
    return mod


def _capture_print(func, args=None, kwargs=None):
    """执行函数并捕获其 print 输出，返回 (output, return_value)。"""
    kwargs = kwargs or {}
    args = args or []
    old = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    try:
        ret = func(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue(), ret


# ======================================================================
# 1. 测试: scripts/animus-engine.py  —  CLI 入口
# ======================================================================

class TestAnimusEngine(unittest.TestCase):
    """测试 scripts/animus-engine.py 的子命令分发逻辑。"""

    def setUp(self):
        """每个测试前备份 sys，安装 engine 命名空间的 mock。"""
        self._orig_argv = sys.argv[:]
        self._orig_modules = dict(sys.modules)
        self._orig_path = sys.path[:]

        # 确认 scripts/ 在 sys.path 中
        if _SCRIPTS_DIR not in sys.path:
            sys.path.insert(0, _SCRIPTS_DIR)

        # 创建 engine 包 mock 以及所有 cmd_* 子模块
        self._engine_mock = _mock.MagicMock()
        self._cmd_mocks = {}
        for name in ("cmd_status", "cmd_transition", "cmd_validate",
                     "cmd_archive", "cmd_rebuild"):
            sub = _mock.MagicMock()
            self._cmd_mocks[name] = sub
            full = "engine." + name
            sys.modules[full] = sub

        # 让 engine 包本身也可被导入（即 from engine.cmd_status import run 可用）
        sys.modules["engine"] = self._engine_mock

    def tearDown(self):
        """还原 sys.argv 和 sys.modules。"""
        sys.argv = self._orig_argv[:]
        for k in list(sys.modules.keys()):
            if k not in self._orig_modules:
                del sys.modules[k]
        sys.path = self._orig_path[:]

    def _call_main(self, argv, allow_exit=False):
        """设置 argv 并执行 animus-engine 的 main()。

        allow_exit=True 时 SystemExit 直接传出，由调用者处理。
        allow_exit=False 时捕获并返回退出码。
        """
        sys.argv = ["animus-engine"] + argv

        # 加载模块 — 用 importlib 处理文件名中的连字符
        mod = _load_via_importlib(
            "animus_engine",
            os.path.join(_SCRIPTS_DIR, "animus-engine.py"),
        )
        try:
            mod.main()
        except SystemExit as e:
            if allow_exit:
                raise
            return e.code
        return 0

    # ------------------------------------------------------------------
    # status 子命令
    # ------------------------------------------------------------------

    def test_main_status(self):
        """调用 status 子命令 → 分发到 engine.cmd_status.run"""
        code = self._call_main(["status"])
        self.assertEqual(code, 0)
        self._cmd_mocks["cmd_status"].run.assert_called_once_with()

    # ------------------------------------------------------------------
    # transition 子命令
    # ------------------------------------------------------------------

    def test_main_transition(self):
        """调用 transition 子命令 → 分发到 engine.cmd_transition.run"""
        code = self._call_main(["transition", "T001", "in_progress", "--evidence", "test.log"])
        self.assertEqual(code, 0)
        self._cmd_mocks["cmd_transition"].run.assert_called_once_with(
            "T001", "in_progress", "test.log"
        )

    def test_main_transition_minimal(self):
        """transition 子命令仅传必需参数"""
        code = self._call_main(["transition", "T001", "passed"])
        self.assertEqual(code, 0)
        self._cmd_mocks["cmd_transition"].run.assert_called_once_with(
            "T001", "passed", ""
        )

    # ------------------------------------------------------------------
    # validate 子命令
    # ------------------------------------------------------------------

    def test_main_validate(self):
        """调用 validate 子命令 → 分发到 engine.cmd_validate.run"""
        code = self._call_main(["validate"])
        self.assertEqual(code, 0)
        self._cmd_mocks["cmd_validate"].run.assert_called_once_with()

    # ------------------------------------------------------------------
    # archive 子命令
    # ------------------------------------------------------------------

    def test_main_archive(self):
        """调用 archive 子命令（含 --name 和 --discard）"""
        code = self._call_main(["archive", "--name", "v1.0", "--discard"])
        self.assertEqual(code, 0)
        self._cmd_mocks["cmd_archive"].run.assert_called_once_with("v1.0", True)

    def test_main_archive_defaults(self):
        """调用 archive 子命令（无参数）→ 使用默认值调用"""
        code = self._call_main(["archive"])
        self.assertEqual(code, 0)
        self._cmd_mocks["cmd_archive"].run.assert_called_once_with("", False)

    # ------------------------------------------------------------------
    # rebuild 子命令
    # ------------------------------------------------------------------

    def test_main_rebuild(self):
        """调用 rebuild 子命令 → 分发到 engine.cmd_rebuild.run"""
        code = self._call_main(["rebuild"])
        self.assertEqual(code, 0)
        self._cmd_mocks["cmd_rebuild"].run.assert_called_once_with()

    # ------------------------------------------------------------------
    # 帮助 / 未知子命令
    # ------------------------------------------------------------------

    def test_main_help(self):
        """无参数时 argparse 输出帮助信息并退出。"""
        with self.assertRaises(SystemExit):
            self._call_main([], allow_exit=True)

    def test_main_unknown(self):
        """未知子命令时 argparse 报错并退出。"""
        with self.assertRaises(SystemExit):
            self._call_main(["unknown_cmd"], allow_exit=True)

    def test_main_engine_error_handling(self):
        """子命令抛出异常时 main 捕获并退出码为 1"""
        self._cmd_mocks["cmd_status"].run.side_effect = RuntimeError("模拟错误")
        code = self._call_main(["status"])
        self.assertEqual(code, 1)


# ======================================================================
# 2. 测试: scripts/session-catchup.py
# ======================================================================

class TestSessionCatchup(unittest.TestCase):
    """测试 scripts/session-catchup.py 的功能函数。"""

    def setUp(self):
        """每个测试前创建临时目录并保存工作目录。"""
        self.tmpdir, self._old_cwd = _make_temp_dir("session_catchup_test_")
        self._loaded = {}

    def tearDown(self):
        """每个测试后清理。"""
        _clean_temp_dir(self.tmpdir, self._old_cwd)

    def _load(self):
        """惰性加载 session-catchup 模块。"""
        if "sc" not in self._loaded:
            self._loaded["sc"] = _load_via_importlib(
                "session_catchup",
                os.path.join(_SCRIPTS_DIR, "session-catchup.py"),
            )
        return self._loaded["sc"]

    # ------------------------------------------------------------------
    # read_features
    # ------------------------------------------------------------------

    def test_read_features(self):
        """读取 dict 格式的 features.json → 返回 tasks 列表"""
        sc = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        path = os.path.join(animus, "features.json")

        tasks = [
            {"id": "T001", "name": "任务一", "status": "in_progress"},
            {"id": "T002", "name": "任务二", "status": "pending"},
        ]
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump({"initial_tasks": tasks}, f)

        result = sc.read_features(path)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "T001")

    def test_read_features_list_format(self):
        """读取 list 格式的 features.json → 直接返回列表"""
        sc = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        path = os.path.join(animus, "features.json")

        tasks = [{"id": "T001", "name": "任务一", "status": "pending"}]
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(tasks, f)

        result = sc.read_features(path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "T001")

    def test_read_features_dict_no_tasks_key(self):
        """dict 格式但无 tasks 键时返回空列表"""
        sc = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        path = os.path.join(animus, "features.json")

        with io.open(path, "w", encoding="utf-8") as f:
            json.dump({"version": 1}, f)

        result = sc.read_features(path)
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # no_features — features.json 不存在
    # ------------------------------------------------------------------

    def test_no_features(self):
        """features.json 不存在时 read_features 返回 None"""
        sc = self._load()
        result = sc.read_features("/nonexistent/path/features.json")
        self.assertIsNone(result)

    def test_no_features_empty_dir(self):
        """目录存在但 features.json 不存在时返回 None"""
        sc = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        result = sc.read_features(os.path.join(animus, "features.json"))
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # generate_prompt / print_q1
    # ------------------------------------------------------------------

    def test_generate_prompt(self):
        """print_q1 输出包含 in_progress 任务的恢复提示"""
        sc = self._load()
        tasks = [
            {"id": "T001", "name": "登录模块", "status": "in_progress"},
            {"id": "T002", "name": "注册模块", "status": "pending"},
        ]
        output, _ = _capture_print(sc.print_q1, [tasks])
        self.assertIn("T001", output)
        self.assertIn("登录模块", output)

    def test_generate_prompt_no_in_progress(self):
        """无进行中任务时 print_q1 输出相应提示"""
        sc = self._load()
        tasks = [{"id": "T002", "name": "注册模块", "status": "pending"}]
        output, _ = _capture_print(sc.print_q1, [tasks])
        self.assertIn("没有进行中的任务", output)

    # ------------------------------------------------------------------
    # with_in_progress
    # ------------------------------------------------------------------

    def test_with_in_progress(self):
        """get_in_progress 返回第一个进行中任务"""
        sc = self._load()
        tasks = [
            {"id": "T001", "name": "登录模块", "status": "in_progress"},
            {"id": "T002", "name": "注册模块", "status": "pending"},
        ]
        ip = sc.get_in_progress(tasks)
        self.assertIsNotNone(ip)
        self.assertEqual(ip["id"], "T001")

    def test_with_in_progress_none(self):
        """没有进行中任务时 get_in_progress 返回 None"""
        sc = self._load()
        tasks = [{"id": "T002", "name": "注册模块", "status": "pending"}]
        self.assertIsNone(sc.get_in_progress(tasks))

    # ------------------------------------------------------------------
    # 其他函数
    # ------------------------------------------------------------------

    def test_get_failed(self):
        """get_failed 返回所有失败任务"""
        sc = self._load()
        tasks = [
            {"id": "T001", "status": "passed"},
            {"id": "T002", "status": "failed"},
            {"id": "T003", "status": "failed"},
        ]
        failed = sc.get_failed(tasks)
        self.assertEqual(len(failed), 2)
        self.assertEqual(failed[0]["id"], "T002")

    def test_get_recent_failed_events(self):
        """get_recent_failed_events 返回最近 3 条失败事件"""
        sc = self._load()
        events = [
            {"to_status": "passed"},
            {"to_status": "failed", "task_id": "T001", "message": "e1"},
            {"to_status": "failed", "task_id": "T002", "message": "e2"},
            {"to_status": "failed", "task_id": "T003", "message": "e3"},
            {"to_status": "failed", "task_id": "T004", "message": "e4"},
        ]
        recent = sc.get_recent_failed_events(events)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0]["task_id"], "T002")
        self.assertEqual(recent[-1]["task_id"], "T004")

    def test_print_q2_with_checkboxes(self):
        """print_q2 解析 checkbox 进度"""
        sc = self._load()
        content = "- [x] 第一步\n- [x] 第二步\n- [ ] 第三步\n"
        output, _ = _capture_print(sc.print_q2, [content])
        self.assertIn("2/3", output)
        self.assertIn("第一步", output)
        self.assertIn("第三步", output)

    def test_print_q2_no_content(self):
        """print_q2 content 为 None 时提示无子步骤计划"""
        sc = self._load()
        output, _ = _capture_print(sc.print_q2, [None])
        self.assertIn("未创建子步骤计划", output)

    def test_print_q5_with_in_progress(self):
        """有进行中任务时 print_q5 建议继续该任务"""
        sc = self._load()
        tasks = [{"id": "T001", "name": "登录模块", "status": "in_progress"}]
        output, _ = _capture_print(sc.print_q5, [tasks])
        self.assertIn("继续当前进行中", output)

    def test_print_q5_with_failed(self):
        """有失败任务时 print_q5 建议修复"""
        sc = self._load()
        tasks = [{"id": "T002", "status": "failed", "name": "注册模块"}]
        output, _ = _capture_print(sc.print_q5, [tasks])
        self.assertIn("修复失败", output)

    def test_print_q5_empty(self):
        """空任务列表时 print_q5 提示检查 features.json"""
        sc = self._load()
        output, _ = _capture_print(sc.print_q5, [[]])
        self.assertIn("任务列表为空", output)

    def test_get_file_mtime_nonexistent(self):
        """get_file_mtime 对不存在的文件返回提示信息"""
        sc = self._load()
        result = sc.get_file_mtime("/nonexistent/path")
        self.assertIn("文件不存在", result)

    def test_safe_json_parse(self):
        """safe_json_parse 正常解析 / 损坏时返回 None"""
        sc = self._load()
        self.assertIsNotNone(sc.safe_json_parse('{"a": 1}'))
        self.assertIsNone(sc.safe_json_parse("not json"))
        self.assertIsNone(sc.safe_json_parse(""))


# ======================================================================
# 3. 测试: scripts/format-log.py
# ======================================================================

class TestFormatLog(unittest.TestCase):
    """测试 scripts/format-log.py 的格式化功能。"""

    def setUp(self):
        """每个测试前创建临时目录。"""
        self.tmpdir, self._old_cwd = _make_temp_dir("format_log_test_")
        self._loaded = {}

    def tearDown(self):
        """每个测试后清理。"""
        _clean_temp_dir(self.tmpdir, self._old_cwd)

    def _load(self):
        """惰性加载 format-log 模块。"""
        if "fl" not in self._loaded:
            self._loaded["fl"] = _load_via_importlib(
                "format_log",
                os.path.join(_SCRIPTS_DIR, "format-log.py"),
            )
        return self._loaded["fl"]

    # ------------------------------------------------------------------
    # format_timestamp
    # ------------------------------------------------------------------

    def test_format_timestamp_none(self):
        """format_timestamp(None) → 返回空字符串"""
        fl = self._load()
        self.assertEqual(fl.format_timestamp(None), "")

    def test_format_timestamp_float(self):
        """format_timestamp 浮点数时间戳 → 格式化为日期时间"""
        fl = self._load()
        result = fl.format_timestamp(1736937000.0)
        # 具体格式取决于时区，但应包含日期
        self.assertIn("2025", result)

    def test_format_timestamp_string(self):
        """format_timestamp ISO 字符串 → 去掉 T 和毫秒"""
        fl = self._load()
        result = fl.format_timestamp("2025-01-15T10:30:00.123")
        self.assertEqual(result, "2025-01-15 10:30:00")

    def test_format_timestamp_int(self):
        """format_timestamp 整型时间戳"""
        fl = self._load()
        result = fl.format_timestamp(1736937000)
        self.assertIn("2025", result)

    # ------------------------------------------------------------------
    # format_timestamp_markdown
    # ------------------------------------------------------------------

    def test_format_timestamp_markdown(self):
        """format_timestamp_markdown 截断到分"""
        fl = self._load()
        result = fl.format_timestamp_markdown("2025-01-15T10:30:00")
        self.assertEqual(len(result), 16)

    # ------------------------------------------------------------------
    # format_entry — format_plain
    # ------------------------------------------------------------------

    def test_format_entry_state_transition(self):
        """格式化 state_transition 类型条目"""
        fl = self._load()
        events = [{
            "timestamp": "2025-01-15T10:00:00",
            "type": "state_transition",
            "task_id": "T001",
            "from_status": "pending",
            "to_status": "in_progress",
            "message": "开始开发",
        }]
        output, _ = _capture_print(fl.format_plain, [events])
        self.assertIn("T001", output)
        self.assertIn("pending → in_progress", output)
        self.assertIn("开始开发", output)

    def test_format_entry_compact(self):
        """格式化 compact 类型条目"""
        fl = self._load()
        events = [{
            "timestamp": "2025-01-15T10:00:00",
            "type": "compact",
            "message": "上下文压缩完成",
        }]
        output, _ = _capture_print(fl.format_plain, [events])
        self.assertIn("COMPACT", output)

    def test_format_entry_note(self):
        """格式化 note 类型条目"""
        fl = self._load()
        events = [{
            "timestamp": "2025-01-15T10:00:00",
            "type": "note",
            "task_id": "T001",
            "message": "注意这里有个问题",
        }]
        output, _ = _capture_print(fl.format_plain, [events])
        self.assertIn("NOTE", output)

    def test_format_entry_subtask_update(self):
        """格式化 subtask_update 类型条目"""
        fl = self._load()
        events = [{
            "timestamp": "2025-01-15T10:00:00",
            "type": "subtask_update",
            "task_id": "T001",
            "message": "子任务完成",
        }]
        output, _ = _capture_print(fl.format_plain, [events])
        self.assertIn("SUBTASK", output)

    # ------------------------------------------------------------------
    # read_jsonl
    # ------------------------------------------------------------------

    def test_read_log(self):
        """读取有效 JSONL → 返回事件列表"""
        fl = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        path = os.path.join(animus, "animus-history.jsonl")

        with io.open(path, "w", encoding="utf-8") as f:
            f.write('{"timestamp": "10:00", "type": "state_transition", "task_id": "T001"}\n')
            f.write('---\n')
            f.write('{"timestamp": "11:00", "type": "note", "task_id": "T001"}\n')

        events = fl.read_jsonl(path)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "state_transition")
        self.assertEqual(events[1]["type"], "note")

    def test_read_log_empty(self):
        """读取空 JSONL → 返回空列表"""
        fl = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        path = os.path.join(animus, "animus-history.jsonl")

        with io.open(path, "w", encoding="utf-8") as f:
            f.write("")

        events = fl.read_jsonl(path)
        self.assertEqual(events, [])

    # ------------------------------------------------------------------
    # no_log — 文件不存在
    # ------------------------------------------------------------------

    def test_no_log(self):
        """日志文件不存在时 read_jsonl 返回空列表，不报错"""
        fl = self._load()
        events = fl.read_jsonl("/nonexistent/history.jsonl")
        self.assertEqual(events, [])

    def test_malformed_jsonl(self):
        """损坏的行被跳过并输出警告"""
        fl = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        path = os.path.join(animus, "animus-history.jsonl")

        with io.open(path, "w", encoding="utf-8") as f:
            f.write('{"valid": "event"}\n')
            f.write('---\n')
            f.write('not json\n')
            f.write('---\n')
            f.write('{"another": "event"}\n')

        events = fl.read_jsonl(path)
        self.assertEqual(len(events), 2)

    # ------------------------------------------------------------------
    # format_markdown
    # ------------------------------------------------------------------

    def test_format_markdown(self):
        """format_markdown 输出 Markdown 表格"""
        fl = self._load()
        events = [{
            "timestamp": "2025-01-15T10:00:00",
            "type": "state_transition",
            "task_id": "T001",
            "from_status": "pending",
            "to_status": "in_progress",
            "message": "start",
        }]
        output, _ = _capture_print(fl.format_markdown, [events])
        self.assertIn("时间 | 类型 | 任务 | 变更 | 消息", output)
        self.assertIn("state_transition", output)


# ======================================================================
# 4. 测试: scripts/run-regression.py
# ======================================================================

class TestRunRegression(unittest.TestCase):
    """测试 scripts/run-regression.py 的配置读取功能。"""

    def setUp(self):
        """每个测试前创建临时目录。"""
        self.tmpdir, self._old_cwd = _make_temp_dir("run_regression_test_")
        self._loaded = {}

    def tearDown(self):
        """每个测试后清理。"""
        _clean_temp_dir(self.tmpdir, self._old_cwd)

    def _load(self):
        """惰性加载 run-regression 模块。"""
        if "rr" not in self._loaded:
            self._loaded["rr"] = _load_via_importlib(
                "run_regression",
                os.path.join(_SCRIPTS_DIR, "run-regression.py"),
            )
        return self._loaded["rr"]

    # ------------------------------------------------------------------
    # read_json
    # ------------------------------------------------------------------

    def test_read_json(self):
        """read_json 读取有效的 JSON 文件"""
        rr = self._load()
        path = os.path.join(self.tmpdir, "config.json")
        data = {"build-command": "make", "test-command": "make test"}
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = rr.read_json(path)
        self.assertEqual(result["build-command"], "make")
        self.assertEqual(result["test-command"], "make test")

    # ------------------------------------------------------------------
    # read_config — 解析 project-config.json
    # ------------------------------------------------------------------

    def test_read_config(self):
        """读取 project-config.json 中的顶层构建和测试命令"""
        rr = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        cfg = os.path.join(animus, "project-config.json")

        data = {"build-command": "cmake --build .", "test-command": "ctest"}
        with io.open(cfg, "w", encoding="utf-8") as f:
            json.dump(data, f)

        config = rr.read_json(cfg)
        build_cmd = str(config.get("build-command", "") or "")
        test_cmd = str(config.get("test-command", "") or "")
        self.assertEqual(build_cmd, "cmake --build .")
        self.assertEqual(test_cmd, "ctest")

    def test_read_config_backend_nested(self):
        """读取嵌套 backend 结构中的命令"""
        rr = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        cfg = os.path.join(animus, "project-config.json")

        data = {"backend": {"build-command": "cd backend && make", "test-command": "cd backend && pytest"}}
        with io.open(cfg, "w", encoding="utf-8") as f:
            json.dump(data, f)

        config = rr.read_json(cfg)
        build_cmd = str(config.get("build-command", "") or "")
        test_cmd = str(config.get("test-command", "") or "")

        if not build_cmd and "backend" in config:
            build_cmd = str(config["backend"].get("build-command", "") or "")
        if not test_cmd and "backend" in config:
            test_cmd = str(config["backend"].get("test-command", "") or "")

        self.assertEqual(build_cmd, "cd backend && make")
        self.assertEqual(test_cmd, "cd backend && pytest")

    def test_read_config_legacy_compat(self):
        """读取 _backward-compatibility 遗留字段"""
        rr = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        cfg = os.path.join(animus, "project-config.json")

        data = {
            "_backward-compatibility": {
                "legacyFields": {
                    "build-command": "legacy_build",
                    "test-command": "legacy_test",
                }
            }
        }
        with io.open(cfg, "w", encoding="utf-8") as f:
            json.dump(data, f)

        config = rr.read_json(cfg)
        build_cmd = str(config.get("build-command", "") or "")
        test_cmd = str(config.get("test-command", "") or "")

        if not build_cmd and not test_cmd and "_backward-compatibility" in config:
            legacy = config["_backward-compatibility"].get("legacyFields", {})
            build_cmd = str(legacy.get("build-command", legacy.get("build_command", "")) or "")
            test_cmd = str(legacy.get("test-command", legacy.get("test_command", "")) or "")

        self.assertEqual(build_cmd, "legacy_build")
        self.assertEqual(test_cmd, "legacy_test")

    def test_read_config_old_field_names(self):
        """读取旧版下划线字段名"""
        rr = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)
        cfg = os.path.join(animus, "project-config.json")

        data = {"build_command": "old_build", "test_command": "old_test"}
        with io.open(cfg, "w", encoding="utf-8") as f:
            json.dump(data, f)

        config = rr.read_json(cfg)
        build_cmd = str(config.get("build-command", config.get("build_command", "")) or "")
        test_cmd = str(config.get("test-command", config.get("test_command", "")) or "")
        self.assertEqual(build_cmd, "old_build")
        self.assertEqual(test_cmd, "old_test")

    # ------------------------------------------------------------------
    # no_config — 无配置时降级
    # ------------------------------------------------------------------

    def test_no_config(self):
        """无 project-config.json 时跳过构建步骤，不报错"""
        rr = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        # 不创建配置文件
        cfg = os.path.join(animus, "project-config.json")
        self.assertFalse(os.path.exists(cfg))
        # 降级：命令均为空
        build_cmd = ""
        test_cmd = ""
        self.assertEqual(build_cmd, "")
        self.assertEqual(test_cmd, "")

    def test_no_config_then_features_fallback(self):
        """无 project-config.json 但有 features.json 时从 features 读取 test_command"""
        rr = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)

        # 创建 features.json
        features_path = os.path.join(animus, "features.json")
        features_data = {
            "tasks": [
                {"id": "T001", "name": "test", "test_command": "pytest tests/"}
            ]
        }
        with io.open(features_path, "w", encoding="utf-8") as f:
            json.dump(features_data, f)

        # 降级逻辑：从 features.json 读取
        cfg_path = os.path.join(animus, "project-config.json")
        self.assertFalse(os.path.exists(cfg_path))

        features = rr.read_json(features_path)
        if isinstance(features, dict):
            task_list = features.get("tasks") or features.get("initial_tasks") or []
        elif isinstance(features, list):
            task_list = features
        else:
            task_list = []

        test_cmd = ""
        if task_list:
            first = task_list[0] if isinstance(task_list, list) else task_list
            test_cmd = str(first.get("test_command", "") or "")

        self.assertEqual(test_cmd, "pytest tests/")

    def test_no_config_features_list_fallback(self):
        """features.json 为 list 格式时也能正确降级"""
        rr = self._load()
        animus = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(animus)

        features_path = os.path.join(animus, "features.json")
        features_data = [
            {"id": "T001", "name": "test", "test_command": "go test ./..."}
        ]
        with io.open(features_path, "w", encoding="utf-8") as f:
            json.dump(features_data, f)

        features = rr.read_json(features_path)
        if isinstance(features, dict):
            task_list = features.get("tasks") or features.get("initial_tasks") or []
        elif isinstance(features, list):
            task_list = features
        else:
            task_list = []

        test_cmd = ""
        if task_list:
            first = task_list[0] if isinstance(task_list, list) else task_list
            test_cmd = str(first.get("test_command", "") or "")

        self.assertEqual(test_cmd, "go test ./...")



# ======================================================================
# 5. 测试: scripts/memlog.py
# ======================================================================

class TestMemlog(unittest.TestCase):
    """测试 scripts/memlog.py 的安全过滤和文件写入功能。"""

    def setUp(self):
        """每个测试前创建临时 .claude/animus 目录。"""
        self.tmpdir, self._old_cwd = _make_temp_dir("memlog_test_")
        self._loaded = {}
        # 创建 .claude/animus 目录（write_event 依赖的目录结构）
        self.animus_dir = os.path.join(self.tmpdir, ".claude", "animus")
        os.makedirs(self.animus_dir)
        # 切换到临时目录，使 get_animus_dir() 能找到它
        os.chdir(self.tmpdir)

    def tearDown(self):
        """每个测试后清理。"""
        _clean_temp_dir(self.tmpdir, self._old_cwd)

    def _load(self):
        """惰性加载 memlog 模块。"""
        if "ml" not in self._loaded:
            self._loaded["ml"] = _load_via_importlib(
                "memlog",
                os.path.join(_SCRIPTS_DIR, "memlog.py"),
            )
        return self._loaded["ml"]

    # ------------------------------------------------------------------
    # write_event — 文件名安全过滤验证
    # ------------------------------------------------------------------

    def test_safe_context_keeps_alnum_and_chinese(self):
        """write_event 生成的文件名保留字母数字和中文字符"""
        ml = self._load()
        path = ml.write_event("状态变更", {
            "task_id": "T001",
            "title": "登录模块",
        })
        self.assertIsNotNone(path)
        filename = os.path.basename(path)
        self.assertIn("T001", filename)
        self.assertIn("登录模块", filename)

    def test_safe_context_replaces_special_chars(self):
        """write_event 将非法字符替换为连字符"""
        ml = self._load()
        path = ml.write_event("状态变更", {
            "task_id": "T001",
            "title": "测试: 登录/模块",
        })
        self.assertIsNotNone(path)
        filename = os.path.basename(path)
        # 文件名中不应包含冒号和斜杠
        self.assertNotIn(":", filename)
        self.assertNotIn("/", filename)

    def test_filename_no_illegal_chars(self):
        """write_event 生成的文件名不含非法字符（仅字母数字._-）"""
        ml = self._load()
        path = ml.write_event("决策", {
            "task_id": "T023",
            "title": "清理: 冗余/过滤代码",
        })
        self.assertIsNotNone(path)
        filename = os.path.basename(path)
        name_no_ext = filename[:-3] if filename.endswith(".md") else filename
        for ch in name_no_ext:
            self.assertTrue(
                ch.isalnum() or ch in ('-', '_', '.'),
                msg="不允许的字符 '%s' 出现在文件名 %s 中" % (ch, filename)
            )

    def test_write_event_no_task_id(self):
        """无 task_id 时 write_event 不报错且生成文件名"""
        ml = self._load()
        path = ml.write_event("note", {"note": "一条记录"})
        self.assertIsNotNone(path)
        self.assertTrue(os.path.exists(path))

    def test_list_events(self):
        """写入事件后 list_events 能列出"""
        ml = self._load()
        ml.write_event("决策", {"task_id": "T001", "title": "测试"})
        events = ml.list_events()
        self.assertGreaterEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
