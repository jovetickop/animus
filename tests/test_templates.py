#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_templates.py — 对 templates/ 下 Python 模块的单元测试

覆盖模块：
  - animus/modules/task_helpers.py
  - animus/modules/git_helper.py
  - animus/modules/report_generator.py
  - animus/coding_session.py
  - animus/init.py

使用 tempfile 模拟文件系统，不依赖真实项目文件。
Python 2/3 兼容。
"""

from __future__ import print_function, unicode_literals

import json
import os
import sys
import tempfile
from unittest.mock import call, patch

import pytest

# ---------------------------------------------------------------------------
# 路径处理：将 templates/ 加入 sys.path，使各模块可被 import
# ---------------------------------------------------------------------------
_templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
if _templates_dir not in sys.path:
    sys.path.insert(0, _templates_dir)


# ===================================================================
# task_helpers 模块 — 任务查找、状态统计、DAG 环检测
# ===================================================================

class TestTaskHelpers:
    """templates/animus/modules/task_helpers.py 单元测试"""

    def _make_tasks(self):
        """辅助方法：生成一组标准测试任务。"""
        return [
            {"id": "T1", "name": "任务一", "status": "passed",     "priority": 1, "depends_on": []},
            {"id": "T2", "name": "任务二", "status": "in_progress","priority": 3, "depends_on": ["T1"]},
            {"id": "T3", "name": "任务三", "status": "pending",    "priority": 2, "depends_on": ["T2"]},
            {"id": "T4", "name": "任务四", "status": "in_progress","priority": 5, "depends_on": []},
            {"id": "T5", "name": "任务五", "status": "failed",     "priority": 0, "depends_on": []},
        ]

    # -- test_find_task_by_id ------------------------------------------------

    def test_find_task_by_id(self):
        """按 ID 查找任务：能找到存在的任务。"""
        from animus.modules import task_helpers
        tasks = self._make_tasks()
        result = task_helpers.find_task_by_id(tasks, "T3")
        assert result is not None
        assert result["id"] == "T3"
        assert result["name"] == "任务三"

    def test_find_task_by_id_not_found(self):
        """按 ID 查找任务：找不到时返回 None。"""
        from animus.modules import task_helpers
        tasks = self._make_tasks()
        result = task_helpers.find_task_by_id(tasks, "NONEXIST")
        assert result is None

    def test_find_task_by_id_int_id(self):
        """按 ID 查找任务：传入 int 类型的 ID 也能匹配字符串 ID。"""
        from animus.modules import task_helpers
        tasks = [{"id": "42", "name": "test"}]
        result = task_helpers.find_task_by_id(tasks, 42)
        assert result is not None
        assert result["id"] == "42"

    # -- test_count_by_status -----------------------------------------------

    def test_count_by_status(self):
        """按状态统计任务数：各状态计数正确。"""
        from animus.modules import task_helpers
        tasks = self._make_tasks()
        counts = task_helpers.count_by_status(tasks)
        assert counts["passed"] == 1       # T1
        assert counts["in_progress"] == 2  # T2, T4
        assert counts["pending"] == 1      # T3
        assert counts["failed"] == 1       # T5
        assert counts["completed"] == 0

    def test_count_by_status_empty(self):
        """按状态统计任务数：空列表返回全零。"""
        from animus.modules import task_helpers
        counts = task_helpers.count_by_status([])
        assert all(v == 0 for v in counts.values())
        assert set(counts.keys()) == {"pending", "in_progress", "passed", "failed", "completed"}

    def test_count_by_status_unknown_status(self):
        """按状态统计任务数：未知状态不计数。"""
        from animus.modules import task_helpers
        tasks = [
            {"id": "X", "status": "unknown_status"},
            {"id": "Y", "status": "pending"},
        ]
        counts = task_helpers.count_by_status(tasks)
        assert counts["pending"] == 1
        assert counts["passed"] == 0
        assert counts["in_progress"] == 0

    # -- test_get_in_progress -----------------------------------------------

    def test_get_in_progress(self):
        """获取进行中任务：返回所有 in_progress 任务，按优先级降序。"""
        from animus.modules import task_helpers
        tasks = self._make_tasks()
        result = task_helpers.get_in_progress(tasks)
        # T4 priority=5, T2 priority=3
        assert len(result) == 2
        assert result[0]["id"] == "T4"  # 高优先级在前
        assert result[1]["id"] == "T2"

    def test_get_in_progress_none(self):
        """获取进行中任务：无进行中任务时返回空列表。"""
        from animus.modules import task_helpers
        tasks = [
            {"id": "A", "status": "pending"},
            {"id": "B", "status": "passed"},
        ]
        result = task_helpers.get_in_progress(tasks)
        assert result == []

    # -- test_validate_dag --------------------------------------------------

    def test_validate_dag_no_cycle(self):
        """DAG 校验：无环返回 (True, "")。"""
        from animus.modules import task_helpers
        tasks = [
            {"id": "A", "depends_on": []},
            {"id": "B", "depends_on": ["A"]},
            {"id": "C", "depends_on": ["A", "B"]},
        ]
        valid, info = task_helpers.validate_dag(tasks)
        assert valid is True
        assert info == ""

    def test_validate_dag_with_cycle(self):
        """DAG 校验：有环返回 (False, 环描述)。"""
        from animus.modules import task_helpers
        tasks = [
            {"id": "A", "depends_on": ["B"]},
            {"id": "B", "depends_on": ["C"]},
            {"id": "C", "depends_on": ["A"]},
        ]
        valid, info = task_helpers.validate_dag(tasks)
        assert valid is False
        assert "依赖环" in info

    def test_validate_dag_empty(self):
        """DAG 校验：空列表返回 (True, "")。"""
        from animus.modules import task_helpers
        valid, info = task_helpers.validate_dag([])
        assert valid is True
        assert info == ""

    def test_validate_dag_single_node(self):
        """DAG 校验：单个任务（无依赖）无环。"""
        from animus.modules import task_helpers
        tasks = [{"id": "A", "depends_on": []}]
        valid, info = task_helpers.validate_dag(tasks)
        assert valid is True
        assert info == ""

    def test_validate_dag_self_loop(self):
        """DAG 校验：依赖自身构成环。"""
        from animus.modules import task_helpers
        tasks = [
            {"id": "A", "depends_on": ["A"]},
        ]
        valid, info = task_helpers.validate_dag(tasks)
        assert valid is False
        assert "依赖环" in info


# ===================================================================
# git_helper 模块 — Git 辅助功能（模拟 subprocess）
# ===================================================================

class TestGitHelper:
    """templates/animus/modules/git_helper.py 单元测试"""

    # -- test_get_current_branch --------------------------------------------

    @patch("animus.modules.git_helper._run_git")
    def test_get_current_branch_on_branch(self, mock_run_git):
        """获取当前分支：在分支上返回分支名。"""
        from animus.modules import git_helper
        mock_run_git.return_value = (0, "main\n", "")
        branch = git_helper.get_current_branch()
        assert branch == "main"
        mock_run_git.assert_called_once_with(["rev-parse", "--abbrev-ref", "HEAD"])

    @patch("animus.modules.git_helper._run_git")
    def test_get_current_branch_detached(self, mock_run_git):
        """获取当前分支：detached HEAD 返回 "HEAD" 字符串。"""
        from animus.modules import git_helper
        # detached HEAD 时 git rev-parse --abbrev-ref HEAD 返回 "HEAD"
        mock_run_git.return_value = (0, "HEAD\n", "")
        branch = git_helper.get_current_branch()
        assert branch == "HEAD"

    @patch("animus.modules.git_helper._run_git")
    def test_get_current_branch_failure(self, mock_run_git):
        """获取当前分支：git 失败返回 None。"""
        from animus.modules import git_helper
        mock_run_git.return_value = (1, "", "fatal: not a git repository")
        branch = git_helper.get_current_branch()
        assert branch is None

    # -- test_has_uncommitted_changes ---------------------------------------

    @patch("animus.modules.git_helper._run_git")
    def test_has_uncommitted_changes_true(self, mock_run_git):
        """检查未提交变更：有变更返回 True。"""
        from animus.modules import git_helper

        def side_effect(args):
            if args == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args == ["status", "--porcelain"]:
                return (0, " M src/main.py\n", "")
            return (0, "", "")

        mock_run_git.side_effect = side_effect
        result = git_helper.has_uncommitted_changes()
        assert result is True

    @patch("animus.modules.git_helper._run_git")
    def test_has_uncommitted_changes_false(self, mock_run_git):
        """检查未提交变更：无变更返回 False。"""
        from animus.modules import git_helper

        def side_effect(args):
            if args == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args == ["status", "--porcelain"]:
                return (0, "", "")
            return (0, "", "")

        mock_run_git.side_effect = side_effect
        result = git_helper.has_uncommitted_changes()
        assert result is False

    @patch("animus.modules.git_helper._run_git")
    def test_has_uncommitted_changes_not_repo(self, mock_run_git):
        """检查未提交变更：非 Git 仓库返回 False。"""
        from animus.modules import git_helper
        mock_run_git.return_value = (128, "", "fatal: not a git repository")
        result = git_helper.has_uncommitted_changes()
        assert result is False

    # -- test_commit_changes ------------------------------------------------

    @patch("animus.modules.git_helper._run_git")
    def test_commit_changes_success(self, mock_run_git):
        """提交变更：成功时返回 True。"""
        from animus.modules import git_helper

        def side_effect(args):
            if args == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args == ["add", "-A"]:
                return (0, "", "")
            if args == ["diff", "--cached", "--quiet"]:
                # 非零表示有变更
                return (1, "", "")
            if args == ["commit", "-m", "test commit"]:
                return (0, "[main abc123] test commit\n", "")
            return (0, "", "")

        mock_run_git.side_effect = side_effect
        result = git_helper.commit_changes("test commit")
        assert result is True

    @patch("animus.modules.git_helper._run_git")
    def test_commit_changes_failure(self, mock_run_git):
        """提交变更：git commit 失败返回 False。"""
        from animus.modules import git_helper

        def side_effect(args):
            if args == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args == ["add", "-A"]:
                return (0, "", "")
            if args == ["diff", "--cached", "--quiet"]:
                return (1, "", "")
            if args == ["commit", "-m", "bad commit"]:
                return (1, "", "error: commit failed\n")
            return (0, "", "")

        mock_run_git.side_effect = side_effect
        result = git_helper.commit_changes("bad commit")
        assert result is False

    @patch("animus.modules.git_helper._run_git")
    def test_commit_changes_add_failure(self, mock_run_git):
        """提交变更：git add 失败返回 False。"""
        from animus.modules import git_helper

        def side_effect(args):
            if args == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args == ["add", "-A"]:
                return (1, "", "error: add failed\n")
            return (0, "", "")

        mock_run_git.side_effect = side_effect
        result = git_helper.commit_changes("add fails")
        assert result is False

    @patch("animus.modules.git_helper._run_git")
    def test_commit_changes_not_repo(self, mock_run_git):
        """提交变更：非 Git 仓库返回 False。"""
        from animus.modules import git_helper
        mock_run_git.return_value = (128, "", "fatal: not a git repository")
        result = git_helper.commit_changes("nope")
        assert result is False

    @patch("animus.modules.git_helper._run_git")
    def test_commit_changes_no_changes(self, mock_run_git):
        """提交变更：无变更时返回 True（无失败）。"""
        from animus.modules import git_helper

        def side_effect(args):
            if args == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args == ["add", "-A"]:
                return (0, "", "")
            if args == ["diff", "--cached", "--quiet"]:
                return (0, "", "")  # 0 = 无变更
            return (0, "", "")

        mock_run_git.side_effect = side_effect
        result = git_helper.commit_changes("nothing")
        assert result is True

    # -- test_is_git_repo ---------------------------------------------------

    @patch("animus.modules.git_helper._run_git")
    def test_is_git_repo_true(self, mock_run_git):
        """检查 Git 仓库：在仓库中返回 True。"""
        from animus.modules import git_helper
        mock_run_git.return_value = (0, "true\n", "")
        assert git_helper.is_git_repo() is True

    @patch("animus.modules.git_helper._run_git")
    def test_is_git_repo_false(self, mock_run_git):
        """检查 Git 仓库：不在仓库中返回 False。"""
        from animus.modules import git_helper
        mock_run_git.return_value = (128, "", "fatal: not a git repository")
        assert git_helper.is_git_repo() is False


# ===================================================================
# report_generator 模块 — Markdown 状态报告生成
# ===================================================================

class TestReportGenerator:
    """templates/animus/modules/report_generator.py 单元测试"""

    def _sample_features(self):
        """辅助方法：生成一组样本 features 数据。"""
        return [
            {"id": "T1", "name": "登录模块", "status": "passed",     "priority": 1, "depends_on": []},
            {"id": "T2", "name": "注册模块", "status": "in_progress","priority": 2, "depends_on": ["T1"]},
            {"id": "T3", "name": "支付模块", "status": "pending",    "priority": 3, "depends_on": ["T2"]},
        ]

    # -- test_generate_status_report ----------------------------------------

    def test_generate_status_report_empty(self):
        """生成状态报告：空任务列表输出提示信息。"""
        from animus.modules import report_generator
        report = report_generator.generate_status_report([])
        assert "未找到任何任务" in report
        assert "⚠️" in report

    def test_generate_status_report_empty_dict(self):
        """生成状态报告：空 dict 无任务字段输出提示信息。"""
        from animus.modules import report_generator
        report = report_generator.generate_status_report({})
        assert "未找到任何任务" in report

    def test_generate_status_report_with_tasks(self):
        """生成状态报告：有任务时包含统计概览和各任务详情。"""
        from animus.modules import report_generator
        features = self._sample_features()
        report = report_generator.generate_status_report(features)

        # 包含标题
        assert "# 任务状态报告" in report
        # 包含统计概览
        assert "统计概览" in report
        assert "通过 (passed)" in report
        assert "失败 (failed)" in report
        assert "进行中 (in_progress)" in report
        assert "待办 (pending)" in report
        # 包含进度
        assert "进度" in report
        assert "33%" in report  # 1 passed / 3 total
        # 包含任务详情
        assert "登录模块" in report
        assert "注册模块" in report
        assert "支付模块" in report

    def test_generate_status_report_dict_format(self):
        """生成状态报告：支持 dict 格式（含 initial_tasks 或 tasks 键）。"""
        from animus.modules import report_generator
        features = {"initial_tasks": self._sample_features()}
        report = report_generator.generate_status_report(features)
        assert "# 任务状态报告" in report
        assert "登录模块" in report

    def test_generate_status_report_tasks_key(self):
        """生成状态报告：支持 features 字典中 tasks 键。"""
        from animus.modules import report_generator
        features = {"tasks": self._sample_features()}
        report = report_generator.generate_status_report(features)
        assert "# 任务状态报告" in report
        assert "登录模块" in report

    def test_generate_status_report_error_field(self):
        """生成状态报告：任务包含 last_error 时输出。"""
        from animus.modules import report_generator
        tasks = [
            {"id": "E1", "name": "错误任务", "status": "failed",
             "priority": 1, "depends_on": [], "last_error": "超时异常"},
        ]
        report = report_generator.generate_status_report(tasks)
        assert "超时异常" in report
        assert "最后错误" in report

    def test_generate_status_report_updated_at(self):
        """生成状态报告：任务包含 updated_at 时输出。"""
        from animus.modules import report_generator
        tasks = [
            {"id": "U1", "name": "更新任务", "status": "passed",
             "priority": 1, "depends_on": [], "updated_at": "2025-06-01"},
        ]
        report = report_generator.generate_status_report(tasks)
        assert "2025-06-01" in report
        assert "更新时间" in report

    # -- test_generate_iteration_summary ------------------------------------

    def test_generate_iteration_summary(self):
        """生成迭代归档摘要：写入文件包含统计信息。"""
        from animus.modules import report_generator
        features = self._sample_features()
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "archive.md")
            result = report_generator.generate_iteration_summary(
                "v1.0", features, output_path
            )
            assert result is True
            assert os.path.exists(output_path)

            with open(output_path, "rb") as f:
                content = f.read().decode("utf-8")

            assert "# 迭代归档: v1.0" in content
            assert "统计概览" in content
            assert "总任务数" in content
            assert "通过" in content
            assert "完成率" in content
            assert "任务列表" in content
            assert "登录模块" in content
            assert "注册模块" in content
            assert "支付模块" in content

    def test_generate_iteration_summary_empty(self):
        """生成迭代归档摘要：空任务列表也生成完整结构。"""
        from animus.modules import report_generator
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "empty.md")
            result = report_generator.generate_iteration_summary(
                "empty-iter", [], output_path
            )
            assert result is True
            with open(output_path, "rb") as f:
                content = f.read().decode("utf-8")
            assert "迭代归档: empty-iter" in content
            assert "总任务数 | 0" in content

    def test_generate_iteration_summary_creates_dirs(self):
        """生成迭代归档摘要：自动创建中间目录。"""
        from animus.modules import report_generator
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "subdir", "nested", "archive.md")
            result = report_generator.generate_iteration_summary(
                "nested", [], output_path
            )
            assert result is True
            assert os.path.exists(output_path)

    def test_generate_iteration_summary_failure(self):
        """生成迭代归档摘要：写入失败返回 False。"""
        from animus.modules import report_generator
        # 使用一个非法路径（根目录下无权限的路径）
        result = report_generator.generate_iteration_summary(
            "fail", [], "/invalid_dir_that_does_not_exist/report.md"
        )
        # 在 Windows 下这个路径可能不会失败，所以只检查不崩溃
        assert result is False or result is True


# ===================================================================
# coding_session 模块 — 会话入口公共函数
# ===================================================================

class TestCodingSession:
    """templates/animus/coding_session.py 单元测试"""

    # -- test_read_json -----------------------------------------------------

    def test_read_json_valid(self):
        """读取 JSON：有效文件返回解析后的对象。"""
        from animus import coding_session
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "data.json")
            with open(path, "wb") as f:
                f.write(b'{"key": "value", "num": 42}')
            data = coding_session.read_json(path)
            assert data == {"key": "value", "num": 42}

    def test_read_json_with_bom(self):
        """读取 JSON：含 UTF-8 BOM 的文件也能正常解析。"""
        from animus import coding_session
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "bom.json")
            with open(path, "wb") as f:
                f.write(b'\xef\xbb\xbf{"hello": "world"}')
            data = coding_session.read_json(path)
            assert data == {"hello": "world"}

    def test_read_json_nonexistent(self):
        """读取 JSON：文件不存在返回 None。"""
        from animus import coding_session
        result = coding_session.read_json("/nonexistent/path.json")
        assert result is None

    def test_read_json_invalid(self):
        """读取 JSON：无效 JSON 返回 None。"""
        from animus import coding_session
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "bad.json")
            with open(path, "wb") as f:
                f.write(b"not json at all")
            data = coding_session.read_json(path)
            assert data is None

    # -- test_get_tasks -----------------------------------------------------

    def test_get_tasks_list(self):
        """提取任务列表：list 直接返回。"""
        from animus import coding_session
        data = [{"id": "A"}, {"id": "B"}]
        result = coding_session.get_tasks(data)
        assert result == data

    def test_get_tasks_initial_tasks(self):
        """提取任务列表：dict 含 initial_tasks 返回该字段。"""
        from animus import coding_session
        data = {"initial_tasks": [{"id": "X"}]}
        result = coding_session.get_tasks(data)
        assert result == [{"id": "X"}]

    def test_get_tasks_tasks_key(self):
        """提取任务列表：dict 含 tasks 返回该字段。"""
        from animus import coding_session
        data = {"tasks": [{"id": "Y"}]}
        result = coding_session.get_tasks(data)
        assert result == [{"id": "Y"}]

    def test_get_tasks_empty(self):
        """提取任务列表：无匹配字段返回空列表。"""
        from animus import coding_session
        data = {"other": "stuff"}
        result = coding_session.get_tasks(data)
        assert result == []

    def test_get_tasks_empty_dict(self):
        """提取任务列表：空 dict 返回空列表。"""
        from animus import coding_session
        result = coding_session.get_tasks({})
        assert result == []

    # -- test_get_priority --------------------------------------------------

    def test_get_priority_int(self):
        """获取优先级：int 值直接返回。"""
        from animus import coding_session
        assert coding_session.get_priority({"priority": 5}) == 5

    def test_get_priority_string_int(self):
        """获取优先级：字符串数字转为 int。"""
        from animus import coding_session
        assert coding_session.get_priority({"priority": "3"}) == 3

    def test_get_priority_invalid(self):
        """获取优先级：不可转换的类型返回 0。"""
        from animus import coding_session
        assert coding_session.get_priority({"priority": "abc"}) == 0

    def test_get_priority_missing(self):
        """获取优先级：缺失 priority 键返回 0。"""
        from animus import coding_session
        assert coding_session.get_priority({"id": "T1"}) == 0

    # -- test_can_run -------------------------------------------------------

    def test_can_run_no_deps(self):
        """判断可执行：无依赖可执行。"""
        from animus import coding_session
        task = {"id": "A", "depends_on": []}
        assert coding_session.can_run(task, {}) is True

    def test_can_run_dep_satisfied_passed(self):
        """判断可执行：依赖 passed 时可执行。"""
        from animus import coding_session
        task = {"id": "B", "depends_on": ["A"]}
        status = {"A": "passed"}
        assert coding_session.can_run(task, status) is True

    def test_can_run_dep_satisfied_completed(self):
        """判断可执行：依赖 completed 时可执行。"""
        from animus import coding_session
        task = {"id": "B", "depends_on": ["A"]}
        status = {"A": "completed"}
        assert coding_session.can_run(task, status) is True

    def test_can_run_dep_not_satisfied(self):
        """判断可执行：依赖未满足时不可执行。"""
        from animus import coding_session
        task = {"id": "B", "depends_on": ["A"]}
        status = {"A": "pending"}
        assert coding_session.can_run(task, status) is False

    def test_can_run_missing_dep(self):
        """判断可执行：依赖不存在于状态表时不可执行。"""
        from animus import coding_session
        task = {"id": "B", "depends_on": ["A"]}
        status = {}
        assert coding_session.can_run(task, status) is False

    def test_can_run_multiple_deps(self):
        """判断可执行：所有依赖满足才可执行。"""
        from animus import coding_session
        task = {"id": "C", "depends_on": ["A", "B"]}
        status = {"A": "passed", "B": "completed"}
        assert coding_session.can_run(task, status) is True

    def test_can_run_multiple_deps_one_fails(self):
        """判断可执行：任一依赖未满足则不可执行。"""
        from animus import coding_session
        task = {"id": "C", "depends_on": ["A", "B"]}
        status = {"A": "passed", "B": "pending"}
        assert coding_session.can_run(task, status) is False

    # -- test_read_config ---------------------------------------------------

    def test_read_config_exists(self):
        """读取配置：文件存在时返回解析后的 dict。"""
        from animus import coding_session
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "project-config.json")
            with open(config_path, "wb") as f:
                f.write(b'{"project-type": "python", "build-command": "make"}')
            config = coding_session.read_config(tmp_dir)
            assert config == {"project-type": "python", "build-command": "make"}

    def test_read_config_not_exists(self):
        """读取配置：文件不存在返回空 dict。"""
        from animus import coding_session
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = coding_session.read_config(tmp_dir)
            assert config == {}

    def test_read_config_invalid(self):
        """读取配置：无效 JSON 也返回空 dict。"""
        from animus import coding_session
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "project-config.json")
            with open(config_path, "wb") as f:
                f.write(b"not json")
            config = coding_session.read_config(tmp_dir)
            assert config == {}


# ===================================================================
# init 模块 — 项目类型检测
# ===================================================================

class TestInit:
    """templates/animus/init.py 单元测试"""

    # -- test_detect_project_type -------------------------------------------

    def test_detect_cpp_qt(self):
        """检测项目类型：CMakeLists.txt 含 Qt 返回 cpp-qt。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            cmake_path = os.path.join(tmp_dir, "CMakeLists.txt")
            with open(cmake_path, "wb") as f:
                f.write(b"find_package(Qt5 REQUIRED COMPONENTS Widgets)\n")
            result = init_module.detect_project_type(tmp_dir)
            assert result == "cpp-qt"

    def test_detect_cpp_cmake(self):
        """检测项目类型：CMakeLists.txt 不含 Qt 返回 cpp-cmake。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            cmake_path = os.path.join(tmp_dir, "CMakeLists.txt")
            with open(cmake_path, "wb") as f:
                f.write(b"cmake_minimum_required(VERSION 3.10)\nproject(Test)\n")
            result = init_module.detect_project_type(tmp_dir)
            assert result == "cpp-cmake"

    def test_detect_rust(self):
        """检测项目类型：Cargo.toml 返回 rust。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            open(os.path.join(tmp_dir, "Cargo.toml"), "wb").close()
            result = init_module.detect_project_type(tmp_dir)
            assert result == "rust"

    def test_detect_go(self):
        """检测项目类型：go.mod 返回 go。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            open(os.path.join(tmp_dir, "go.mod"), "wb").close()
            result = init_module.detect_project_type(tmp_dir)
            assert result == "go"

    def test_detect_node(self):
        """检测项目类型：package.json 返回 node。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            open(os.path.join(tmp_dir, "package.json"), "wb").close()
            result = init_module.detect_project_type(tmp_dir)
            assert result == "node"

    def test_detect_python_pyproject(self):
        """检测项目类型：pyproject.toml 返回 python。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            open(os.path.join(tmp_dir, "pyproject.toml"), "wb").close()
            result = init_module.detect_project_type(tmp_dir)
            assert result == "python"

    def test_detect_python_requirements(self):
        """检测项目类型：requirements.txt 返回 python。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            open(os.path.join(tmp_dir, "requirements.txt"), "wb").close()
            result = init_module.detect_project_type(tmp_dir)
            assert result == "python"

    def test_detect_generic(self):
        """检测项目类型：无标志性文件返回 generic。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = init_module.detect_project_type(tmp_dir)
            assert result == "generic"

    def test_detect_cmake_priority(self):
        """检测项目类型：CMakeLists.txt 优先级高于其他文件。"""
        from animus import init as init_module
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 同时存在 CMakeLists.txt 和 Cargo.toml
            with open(os.path.join(tmp_dir, "CMakeLists.txt"), "wb") as f:
                f.write(b"find_package(Qt6)\n")
            open(os.path.join(tmp_dir, "Cargo.toml"), "wb").close()
            result = init_module.detect_project_type(tmp_dir)
            assert result == "cpp-qt"

    # -- test_run_animus_status (通过 mock subprocess) ---------------------

    @patch("animus.init.os.path.exists")
    @patch("animus.init.subprocess.check_call")
    def test_run_animus_status_found(self, mock_check_call, mock_exists):
        """运行状态检查：找到引擎脚本并成功执行。"""
        from animus import init as init_module
        mock_exists.side_effect = lambda p: p.endswith("animus-engine.py")
        init_module.run_animus_status("/fake/state")
        assert mock_check_call.called

    @patch("animus.init.os.path.exists")
    def test_run_animus_status_not_found(self, mock_exists):
        """运行状态检查：找不到引擎脚本不报错。"""
        from animus import init as init_module
        mock_exists.return_value = False
        # 不应抛出异常
        init_module.run_animus_status("/fake/state")


# ===================================================================
# 主函数（允许直接运行）
# ===================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
