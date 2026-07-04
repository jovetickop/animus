#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_engine_extras.py

单元测试覆盖：
  - scripts/engine/cmd_status.py   (status / recommend)
  - scripts/engine/cmd_archive.py  (archive)
  - scripts/engine/cmd_rebuild.py  (rebuild)
  - scripts/memlog.py              (memlog write)

使用 unittest.mock.patch + tempfile 模拟文件系统。
"""

from __future__ import print_function, unicode_literals

import json
import os
import sys
import tempfile

import pytest
from unittest.mock import patch, MagicMock

# ── 将被测模块加入 sys.path ──────────────────────────────────────────
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
_ENGINE_DIR = os.path.join(_SCRIPTS_DIR, "engine")
for _p in (_ENGINE_DIR, _SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cmd_status
import cmd_archive
import cmd_rebuild
import memlog


# ====================================================================
# 工具函数
# ====================================================================

def _write_json(path, data):
    """将 data 以 UTF-8 JSON 写入 path。"""
    with open(path, "wb") as f:
        content = json.dumps(data, ensure_ascii=False, indent=2)
        if isinstance(content, str):
            f.write(content.encode("utf-8"))
        else:
            f.write(content)


def _read_json(path):
    """读取 UTF-8 JSON 文件。"""
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


# ====================================================================
# cmd_status — run()
# ====================================================================

class TestCountDeferred:
    """测试 _count_deferred() 函数"""

    def test_no_deferred_file(self):
        """deferred-work.md 不存在时返回 0"""
        with tempfile.TemporaryDirectory() as tmp:
            count = cmd_status._count_deferred(tmp)
            assert count == 0

    def test_empty_deferred_file(self):
        """deferred-work.md 为空时返回 0"""
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "deferred-work.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("# 延迟工作记录\n\n")
            count = cmd_status._count_deferred(tmp)
            assert count == 0

    def test_deferred_with_items(self):
        """有未完成的 defer 条目时返回正确数量"""
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "deferred-work.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("# 延迟工作记录\n\n")
                f.write("## 2026-07-04\n")
                f.write("- [ ] src/a.cpp:1 问题A\n")
                f.write("- [ ] src/b.cpp:2 问题B\n")
            count = cmd_status._count_deferred(tmp)
            assert count == 2

    def test_deferred_with_mixed_items(self):
        """完成的条目（[x]）不计入待办"""
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "deferred-work.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("# 延迟工作记录\n\n")
                f.write("## 2026-07-04\n")
                f.write("- [ ] src/a.cpp:1 未完成\n")
                f.write("- [x] src/b.cpp:2 已完成\n")
                f.write("- [ ] src/c.cpp:3 未完成\n")
            count = cmd_status._count_deferred(tmp)
            assert count == 2

    def test_deferred_read_error(self):
        """读取失败时不抛异常，返回 0"""
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "deferred-work.md")
            # 创建不可读的文件（取决于权限）
            with open(p, "w", encoding="utf-8") as f:
                f.write("- [ ] 测试\n")
            count = cmd_status._count_deferred(tmp)
            assert count >= 1

class TestCmdStatusRun:
    """测试 cmd_status.run() 主流程"""

    def test_status_empty_tasks(self):
        """无任务时输出 INFO"""
        data = {"metadata": {}, "tasks": {}}
        with patch.object(cmd_status, "_find_features_json",
                          return_value="/fake/features.json"):
            with patch.object(cmd_status, "_read_json", return_value=data):
                output = cmd_status.run()
        assert "INFO" in output, "应在无任务时输出 INFO"
        assert "无任务数据" in output, "应提示无任务数据"

    def test_status_with_tasks(self):
        """有任务时输出统计"""
        data = {
            "metadata": {},
            "tasks": {
                "T001": {"id": "T001", "name": "登录页面", "status": "passed"},
                "T002": {"id": "T002", "name": "注册流程", "status": "in_progress"},
                "T003": {"id": "T003", "name": "忘记密码", "status": "pending"},
            },
        }
        with patch.object(cmd_status, "_find_features_json",
                          return_value="/fake/features.json"):
            with patch.object(cmd_status, "_read_json", return_value=data):
                output = cmd_status.run()
        # 统计概览标题
        assert "任务状态报告" in output
        # 总任务数 = 3
        assert "总任务数" in output
        assert "3" in output
        # 各状态都有
        assert "[PASS]" in output
        assert "[RUN ]" in output
        assert "[PEND]" in output


# ====================================================================
# cmd_status — _recommend_next()
# ====================================================================

class TestRecommendNext:
    """测试 _recommend_next() 推荐逻辑"""

    def test_recommend_pending(self):
        """有待办任务时推荐 /animus-dev"""
        features = {
            "tasks": {
                "T001": {"id": "T001", "status": "pending"},
            },
        }
        cmd, reason = cmd_status._recommend_next(features)
        assert cmd == "/animus-dev", "有待办应推荐 /animus-dev"
        assert "待办" in reason

    def test_recommend_in_progress(self):
        """有进行中任务时推荐继续"""
        features = {
            "tasks": {
                "T001": {"id": "T001", "status": "in_progress"},
            },
        }
        cmd, reason = cmd_status._recommend_next(features)
        assert cmd == "/animus-dev", "进行中应推荐 /animus-dev"
        assert "进行中" in reason

    def test_recommend_all_passed(self):
        """全部通过时推荐归档"""
        features = {
            "tasks": {
                "T001": {"id": "T001", "status": "passed"},
                "T002": {"id": "T002", "status": "passed"},
            },
        }
        cmd, reason = cmd_status._recommend_next(features)
        assert cmd == "/animus-archive", "全部通过应推荐 /animus-archive"
        assert "归档" in reason


# ====================================================================
# cmd_archive — run()
# ====================================================================

class TestCmdArchive:
    """测试 cmd_archive.run() 归档流程"""

    @pytest.fixture
    def temp_animus(self):
        """创建临时 .claude/animus/ 环境，返回 animus_dir 路径。"""
        with tempfile.TemporaryDirectory(prefix="animus_test_") as tmpdir:
            animus_dir = os.path.join(tmpdir, ".claude", "animus")
            os.makedirs(animus_dir)
            yield animus_dir

    def test_archive_creates_directory(self, temp_animus):
        """归档应创建 archive/ 及 iter-xxx 子目录"""
        features = {
            "metadata": {"project": "demo"},
            "tasks": {
                "T001": {"id": "T001", "title": "登录", "status": "passed"},
            },
        }
        _write_json(os.path.join(temp_animus, "features.json"), features)

        with patch.object(cmd_archive, "_find_animus_dir",
                          return_value=temp_animus):
            cmd_archive.run()

        archive_dir = os.path.join(temp_animus, "archive")
        assert os.path.isdir(archive_dir), "archive 目录应被创建"

        iters = [d for d in os.listdir(archive_dir) if d.startswith("iter-")]
        assert len(iters) == 1, "应恰好有一个迭代目录"
        assert "001" in iters[0], "迭代编号应为 001"

    def test_archive_clears_features(self, temp_animus):
        """归档后 features.json 的 tasks 应被清空"""
        features = {
            "metadata": {"project": "demo"},
            "tasks": {
                "T001": {"id": "T001", "title": "登录", "status": "passed"},
            },
        }
        fpath = os.path.join(temp_animus, "features.json")
        _write_json(fpath, features)

        with patch.object(cmd_archive, "_find_animus_dir",
                          return_value=temp_animus):
            cmd_archive.run()

        cleared = _read_json(fpath)
        assert cleared["tasks"] == {}, "归档后 tasks 应为空字典"
        assert "metadata" in cleared, "metadata 应被保留"

    def test_archive_iteration_number(self, temp_animus):
        """连续归档时编号应递增"""
        features = {
            "metadata": {},
            "tasks": {
                "T001": {"id": "T001", "title": "任务", "status": "passed"},
            },
        }
        fpath = os.path.join(temp_animus, "features.json")

        # 第一次归档 → iter-001
        _write_json(fpath, features)
        with patch.object(cmd_archive, "_find_animus_dir",
                          return_value=temp_animus):
            cmd_archive.run()
        # 第二次归档 → iter-002
        _write_json(fpath, features)
        with patch.object(cmd_archive, "_find_animus_dir",
                          return_value=temp_animus):
            cmd_archive.run()

        archive_dir = os.path.join(temp_animus, "archive")
        iters = sorted(d for d in os.listdir(archive_dir) if d.startswith("iter-"))
        assert len(iters) == 2, "应有两次归档"
        assert "iter-001" in iters[0], "第一次应为 iter-001"
        assert "iter-002" in iters[1], "第二次应为 iter-002"


# ====================================================================
# cmd_rebuild — run()
# ====================================================================

class TestCmdRebuild:
    """测试 cmd_rebuild.run() 重建流程"""

    @pytest.fixture
    def temp_animus(self):
        """创建临时 .claude/animus/ 环境 + memlog/ 子目录。"""
        with tempfile.TemporaryDirectory(prefix="rebuild_test_") as tmpdir:
            animus_dir = os.path.join(tmpdir, ".claude", "animus")
            os.makedirs(os.path.join(animus_dir, "memlog"))
            yield animus_dir

    def test_rebuild_no_memlog(self, temp_animus):
        """memlog 目录不存在时给出提示"""
        # 删掉 memlog 目录
        shutil = __import__("shutil")
        shutil.rmtree(os.path.join(temp_animus, "memlog"))

        with patch.object(cmd_rebuild, "_find_animus_dir",
                          return_value=temp_animus):
            # run() 打印消息，不抛出异常
            cmd_rebuild.run()

        # 验证没有新的 features.json 被写出
        fpath = os.path.join(temp_animus, "features.json")
        assert not os.path.isfile(fpath), "不应写入 features.json"

    def test_rebuild_with_events(self, temp_animus):
        """有事件文件时能重建 features.json"""
        memlog_dir = os.path.join(temp_animus, "memlog")

        # 创建"创建任务"事件
        create_event = (
            "---\n"
            "type: 创建任务\n"
            "title: 用户登录\n"
            "status: pending\n"
            "priority: 1\n"
            "---\n"
            "\n"
            "# 创建任务：用户登录\n"
        )
        with open(os.path.join(memlog_dir, "2025-01-15-0930-创建任务-T001-用户登录.md"),
                  "wb") as f:
            f.write(create_event.encode("utf-8"))

        # 创建"状态变更"事件 — 变更为 passed
        status_event = (
            "---\n"
            "type: 状态变更\n"
            "status: passed\n"
            "---\n"
            "\n"
            "# 状态变更：用户登录 → 通过\n"
        )
        with open(os.path.join(memlog_dir,
                               "2025-01-15-1000-状态变更-T001-通过.md"),
                  "wb") as f:
            f.write(status_event.encode("utf-8"))

        with patch.object(cmd_rebuild, "_find_animus_dir",
                          return_value=temp_animus):
            cmd_rebuild.run()

        # 验证 features.json 被写出
        fpath = os.path.join(temp_animus, "features.json")
        assert os.path.isfile(fpath), "features.json 应被重建"

        data = _read_json(fpath)
        assert "tasks" in data, "应有 tasks"
        assert "T001" in data["tasks"], "应有 T001 任务"
        assert data["tasks"]["T001"]["status"] == "passed", "状态应为 passed"
        assert data["metadata"]["event_count"] == 2, "应统计到 2 个事件"


# ====================================================================
# memlog — write_event()
# ====================================================================

class TestMemlog:
    """测试 memlog.write_event()"""

    @pytest.fixture
    def temp_animus(self):
        """创建临时 .claude/animus/ 环境。"""
        with tempfile.TemporaryDirectory(prefix="memlog_test_") as tmpdir:
            animus_dir = os.path.join(tmpdir, ".claude", "animus")
            os.makedirs(animus_dir)
            yield animus_dir

    def test_memlog_write_event(self, temp_animus):
        """写入事件应创建 .md 文件，内容含 YAML frontmatter"""
        with patch.object(memlog, "get_animus_dir",
                          return_value=temp_animus):
            path = memlog.write_event(
                "创建任务",
                {"task_id": "T001", "title": "用户注册", "status": "pending"},
            )

        assert path is not None, "应返回文件路径"
        assert os.path.isfile(path), "文件应实际存在"
        assert path.endswith(".md"), "应为 .md 文件"

        # 内容包含 frontmatter
        with open(path, "rb") as f:
            content = f.read().decode("utf-8")
        assert "---" in content, "应包含 YAML frontmatter 分隔符"
        assert "type: 创建任务" in content
        assert "task_id: T001" in content
        assert "title: 用户注册" in content
        # 文件体
        assert "# 创建任务" in content

    def test_memlog_cn_filename(self, temp_animus):
        """中文标题应出现在文件名中"""
        with patch.object(memlog, "get_animus_dir",
                          return_value=temp_animus):
            path = memlog.write_event(
                "创建任务",
                {"task_id": "T002", "title": "中文功能测试"},
            )

        assert path is not None
        basename = os.path.basename(path)
        # 中文"中文功能测试"应保留在文件名中
        assert "中文功能测试" in basename, "中文标题应出现在文件名"
        assert "T002" in basename, "任务 ID 应出现在文件名"
        # 验证整体格式：时间戳-类型-Txxx-标题.md
        assert basename.startswith("20"), "应以年份开头"
        assert "创建任务" in basename, "事件类型应出现在文件名"
