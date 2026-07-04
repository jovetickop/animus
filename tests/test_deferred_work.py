# -*- coding: utf-8 -*-
"""
测试 deferred-work 管理模块

覆盖：
- 空文件读取
- 追加单条记录
- 追加多条记录（同日期合并）
- 清空文件
- 文件不存在时 append 自动创建
- 多日期分组
"""

import os
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import deferred_work as dw


class TestDeferredWork:
    """deferred_work 模块基础功能测试"""

    def test_read_nonexistent_returns_empty(self):
        """文件不存在时 read 返回空字符串"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            content = dw.read(d)
            assert content == ""

    def test_append_creates_file(self):
        """追加记录时如果文件不存在则自动创建"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            dw.append_entry("src/main.cpp:42 空指针风险", d)
            assert os.path.exists(os.path.join(d, "deferred-work.md"))

    def test_append_content(self):
        """追加一条记录检查内容正确"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            dw.append_entry("src/main.cpp:42 空指针风险", d)
            content = dw.read(d)
            assert "src/main.cpp:42 空指针风险" in content
            assert "- [ ]" in content

    def test_append_multiple_same_date(self):
        """同一天追加多条记录共享一个日期标题"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            dw.append_entry("src/a.cpp:1 问题A", d)
            dw.append_entry("src/b.cpp:2 问题B", d)
            content = dw.read(d)
            # 两条记录都存在
            assert "src/a.cpp:1 问题A" in content
            assert "src/b.cpp:2 问题B" in content
            # 日期标题只出现一次
            today = __import__("datetime").date.today().isoformat()
            assert content.count(today) == 1

    def test_append_with_existing_content(self):
        """在已有内容的文件上追加保留旧内容"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            dw.append_entry("旧问题", d)
            dw.append_entry("新问题", d)
            content = dw.read(d)
            # 验证顺序：原先的在前面
            assert content.index("旧问题") < content.index("新问题")

    def test_clear(self):
        """清空后只剩标题行"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            dw.append_entry("某问题", d)
            dw.clear(d)
            content = dw.read(d)
            assert "# 延迟工作记录" in content
            assert "某问题" not in content

    def test_clear_empty_file(self):
        """清空一个刚创建的空文件不报错"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            dw.clear(d)
            content = dw.read(d)
            assert "# 延迟工作记录" in content

    def test_append_unicode(self):
        """中文字符正确处理"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            dw.append_entry("src/数据.cpp:12 缓存未清理", d)
            content = dw.read(d)
            assert "src/数据.cpp:12 缓存未清理" in content

    def test_get_path_default(self):
        """默认路径指向项目 .claude/animus/"""
        path = dw.get_path()
        assert path.endswith(".claude/animus/deferred-work.md") or \
               path.endswith(".claude\\animus\\deferred-work.md")

    def test_get_path_custom(self):
        """指定目录后路径正确"""
        path = dw.get_path("/my/project/.claude/animus")
        assert "deferred-work.md" in path

    def test_append_entry(self):
        """追加一条 deferred entry 能正确写入文件"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            dw.append_entry("src/main.cpp:42 内存泄漏", d)
            content = dw.read(d)
            assert "src/main.cpp:42 内存泄漏" in content
            assert "- [ ]" in content
            # 验证日期标题存在
            today = __import__("datetime").date.today().isoformat()
            assert today in content

    def test_read_entries(self):
        """读取功能正常：空文件和含内容文件"""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, ".claude", "animus")
            os.makedirs(d)
            # 空文件读取
            content_empty = dw.read(d)
            assert content_empty == ""
            # 写入内容后读取
            dw.append_entry("test_entry", d)
            content = dw.read(d)
            assert "test_entry" in content
            assert len(content) > 0
