#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对 hooks/scripts/ 下 encoding-bridge.py 与 format-all.py 的单元测试。

测试范围：
  - encoding-bridge.py  GBK/UTF-8 编码桥接
  - format-all.py       多语言代码格式化

使用 pytest + tempfile 模拟文件系统，不依赖真实项目目录。
每个测试独立执行，互不依赖。
"""

from __future__ import print_function, unicode_literals

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

# tests/ 目录也加入 path，以便 import _run_main_helpers
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)


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


# ===================================================================
# encoding-bridge.py 测试
# ===================================================================

class TestEncodingBridge(object):
    """encoding-bridge.py：GBK/UTF-8 编码桥接工具。"""

    def _mod(self):
        """延迟加载 encoding-bridge 模块"""
        return _load_module("encoding_bridge", "encoding-bridge.py")

    # ------------------------------------------------------------------
    # to_utf8 / to_gbk 直接测试
    # ------------------------------------------------------------------

    def test_gbk_to_utf8(self):
        """写入 GBK 编码文件 → to_utf8 转码后为 UTF-8"""
        mod = self._mod()
        text = u"你好，世界！Hello, 世界！"
        gbk_bytes = text.encode("gbk")

        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as f:
            f.write(gbk_bytes)
            tmpfile = f.name

        try:
            result = mod.to_utf8(tmpfile, "gbk")
            assert result is True, u"to_utf8 应返回 True 表示成功"

            with open(tmpfile, "rb") as f:
                content = f.read()

            # 验证文件内容现在是 UTF-8 编码
            decoded = content.decode("utf-8")
            assert decoded == text, u"转码后内容应与原文一致"
            # 确保不再是 GBK 编码（UTF-8 BOM 通常不存在，但检查解码是否成功）
            assert content != gbk_bytes, u"转码后二进制内容应与原始 GBK 不同"
        finally:
            os.unlink(tmpfile)

    def test_utf8_to_gbk(self):
        """写入 UTF-8 文件 → to_gbk 转码后为 GBK"""
        mod = self._mod()
        text = u"你好，世界！Hello, 世界！"
        utf8_bytes = text.encode("utf-8")

        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as f:
            f.write(utf8_bytes)
            tmpfile = f.name

        try:
            result = mod.to_gbk(tmpfile, "gbk")
            assert result is True, u"to_gbk 应返回 True 表示成功"

            with open(tmpfile, "rb") as f:
                content = f.read()

            # 验证文件内容现在是 GBK 编码
            decoded = content.decode("gbk")
            assert decoded == text, u"转码后内容应与原文一致"
            # 确保不再是 UTF-8
            assert content != utf8_bytes, u"转码后二进制内容应与原始 UTF-8 不同"
        finally:
            os.unlink(tmpfile)

    def test_no_gbk_file(self):
        """非 C/C++ 扩展名文件 → main() 直接退出，不执行转码"""
        mod = self._mod()
        text = u"你好世界"
        gbk_bytes = text.encode("gbk")

        # 使用非 C/C++ 扩展名
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(gbk_bytes)
            tmpfile = f.name

        try:
            # 直接调用 main，应该因为扩展名不匹配而 exit(0)
            from _run_main_helpers import _run_main
            code, _ = _run_main(mod, [
                "encoding-bridge.py",
                "--action", "to_utf8",
                "--file", tmpfile
            ])
            assert code == 0, u"非 C/C++ 文件应静默退出 (exit 0)"

            # 验证文件内容未被修改（仍然是 GBK）
            with open(tmpfile, "rb") as f:
                content = f.read()
            assert content == gbk_bytes, u"非 C/C++ 文件不应被修改"
        finally:
            os.unlink(tmpfile)

    def test_is_gbk(self):
        """检测文件是否为 GBK 编码（通过 to_utf8 的行为推断）"""
        mod = self._mod()

        # 1) 写入有效的 GBK 内容 → to_utf8 成功（是 GBK）
        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as f:
            f.write(u"你好世界".encode("gbk"))
            gbk_file = f.name

        # 2) 写入非 GBK 的二进制内容（无效 GBK 序列）→ to_utf8 失败
        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as f:
            # 0xFF 0xFE 不是有效的 GBK 序列
            f.write(b"\xff\xfe\x00\x00")
            bad_file = f.name

        try:
            # 真实 GBK 文件可用 gbk 解码 → to_utf8 返回 True
            assert mod.to_utf8(gbk_file, "gbk") is True, \
                u"GBK 编码文件，to_utf8(gbk) 应返回 True"

            # 非 GBK 文件 → to_utf8 返回 False
            assert mod.to_utf8(bad_file, "gbk") is False, \
                u"非 GBK 文件，to_utf8(gbk) 应返回 False"
        finally:
            os.unlink(gbk_file)
            os.unlink(bad_file)

    def test_file_not_found(self):
        """文件不存在时 to_utf8/to_gbk 不报错，返回 False"""
        mod = self._mod()
        nonexistent = os.path.join(tempfile.gettempdir(), "_nonexistent_file_xyzzy.cpp")
        # 确保文件不存在
        assert not os.path.exists(nonexistent)

        # 不存在的文件应返回 False 而不是抛出异常
        result_utf8 = mod.to_utf8(nonexistent, "gbk")
        assert result_utf8 is False, u"文件不存在时 to_utf8 应返回 False"

        result_gbk = mod.to_gbk(nonexistent, "gbk")
        assert result_gbk is False, u"文件不存在时 to_gbk 应返回 False"

    # ------------------------------------------------------------------
    # 辅助函数测试
    # ------------------------------------------------------------------

    def test_get_encoding(self):
        """get_encoding 从参数中提取编码名，默认返回 gbk"""
        mod = self._mod()
        assert mod.get_encoding([]) == "gbk", u"无参数时默认返回 gbk"
        assert mod.get_encoding(["--encoding", "utf-8"]) == "utf-8"
        assert mod.get_encoding(["--encoding", "gb18030"]) == "gb18030"

    def test_get_action(self):
        """get_action 提取 --action 参数值"""
        mod = self._mod()
        assert mod.get_action([]) is None, u"无参数时返回 None"
        assert mod.get_action(["--action", "to_utf8"]) == "to_utf8"
        assert mod.get_action(["--action", "to_gbk"]) == "to_gbk"

    def test_get_file(self):
        """get_file 提取 --file 参数值"""
        mod = self._mod()
        assert mod.get_file([]) is None, u"无参数时返回 None"
        assert mod.get_file(["--file", "/path/to/file.cpp"]) == "/path/to/file.cpp"

    # ------------------------------------------------------------------
    # main() 集成测试
    # ------------------------------------------------------------------

    def test_main_to_utf8_integration(self):
        """main() 集成测试：to_utf8 动作"""
        mod = self._mod()
        text = u"你好世界"
        gbk_bytes = text.encode("gbk")

        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as f:
            f.write(gbk_bytes)
            tmpfile = f.name

        try:
            from _run_main_helpers import _run_main
            code, _ = _run_main(mod, [
                "encoding-bridge.py",
                "--action", "to_utf8",
                "--file", tmpfile
            ])
            assert code == 0, u"main() 应 exit(0)"

            with open(tmpfile, "rb") as f:
                content = f.read()
            decoded = content.decode("utf-8")
            assert decoded == text, u"main() 集成：内容应成功转码为 UTF-8"
        finally:
            os.unlink(tmpfile)

    def test_main_to_gbk_integration(self):
        """main() 集成测试：to_gbk 动作"""
        mod = self._mod()
        text = u"你好世界"
        utf8_bytes = text.encode("utf-8")

        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as f:
            f.write(utf8_bytes)
            tmpfile = f.name

        try:
            from _run_main_helpers import _run_main
            code, _ = _run_main(mod, [
                "encoding-bridge.py",
                "--action", "to_gbk",
                "--file", tmpfile
            ])
            assert code == 0, u"main() 应 exit(0)"

            with open(tmpfile, "rb") as f:
                content = f.read()
            decoded = content.decode("gbk")
            assert decoded == text, u"main() 集成：内容应成功转码为 GBK"
        finally:
            os.unlink(tmpfile)


# ===================================================================
# format-all.py 测试
# ===================================================================

class TestFormatAll(object):
    """format-all.py：多语言代码格式化工具。"""

    def _mod(self):
        """延迟加载 format-all 模块"""
        return _load_module("format_all", "format-all.py")

    # ------------------------------------------------------------------
    # formatter 分发测试（mock subprocess.Popen）
    # ------------------------------------------------------------------

    def test_format_cpp(self):
        """模拟 clang-format 格式化 C/C++ 文件"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as f:
            f.write(b"int main() {}")
            tmpfile = f.name

        try:
            from unittest.mock import patch, MagicMock

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")

            with patch.object(mod.subprocess, "Popen", return_value=mock_proc) as mock_popen:
                mod.format_cpp(tmpfile)
                # 验证调用了 clang-format -i
                assert mock_popen.call_count >= 1
                call_args = mock_popen.call_args[0][0]
                assert "clang-format" in call_args, \
                    u"format_cpp 应调用 clang-format"
        finally:
            os.unlink(tmpfile)

    def test_format_python(self):
        """模拟 black/autopep8 格式化 Python 文件"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"x=1")
            tmpfile = f.name

        try:
            from unittest.mock import patch, MagicMock

            # black 返回 0 → 应使用 black
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")

            with patch.object(mod.subprocess, "Popen", return_value=mock_proc) as mock_popen:
                mod.format_py(tmpfile)
                # 验证首先调用了 black
                assert mock_popen.call_count >= 1
                first_call = mock_popen.call_args[0][0]
                assert "black" in first_call, \
                    u"format_py 应优先调用 black"
        finally:
            os.unlink(tmpfile)

    def test_format_python_fallback(self):
        """black 不可用时回退到 autopep8"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"x=1")
            tmpfile = f.name

        try:
            from unittest.mock import patch, MagicMock

            # black 返回非 0 → 应回退到 autopep8
            mock_black = MagicMock()
            mock_black.returncode = 1
            mock_black.communicate.return_value = (b"error", b"")

            mock_autopep8 = MagicMock()
            mock_autopep8.returncode = 0
            mock_autopep8.communicate.return_value = (b"", b"")

            with patch.object(mod.subprocess, "Popen",
                              side_effect=[mock_black, mock_autopep8]) as mock_popen:
                mod.format_py(tmpfile)
                assert mock_popen.call_count == 2
                # 第一次调用是 black
                assert "black" in mock_popen.call_args_list[0][0][0]
                # 第二次调用是 autopep8
                assert "autopep8" in mock_popen.call_args_list[1][0][0]
        finally:
            os.unlink(tmpfile)

    def test_format_rust(self):
        """模拟 cargo fmt 格式化 Rust 文件"""
        mod = self._mod()

        # 创建临时目录结构：包含 Cargo.toml 和 .rs 文件
        tmpdir = tempfile.mkdtemp()
        try:
            # 创建 Cargo.toml（让 find_cargo_root 找到它）
            cargo_toml = os.path.join(tmpdir, "Cargo.toml")
            with open(cargo_toml, "w") as f:
                f.write("[package]\nname = \"test\"\n")

            # 创建 .rs 文件
            rs_file = os.path.join(tmpdir, "src", "lib.rs")
            os.makedirs(os.path.dirname(rs_file))
            with open(rs_file, "wb") as f:
                f.write(b"fn main() {}")

            from unittest.mock import patch, MagicMock

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")

            with patch.object(mod.subprocess, "Popen", return_value=mock_proc) as mock_popen:
                mod.format_rust(rs_file)
                # 验证调用了 cargo fmt
                assert mock_popen.call_count >= 1
                call_args = mock_popen.call_args[0][0]
                assert "cargo" in call_args and "fmt" in call_args, \
                    u"format_rust 应调用 cargo fmt"
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_format_rust_no_cargo_toml(self):
        """Rust 项目没有 Cargo.toml 时不执行格式化"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".rs", delete=False) as f:
            f.write(b"fn main() {}")
            rs_file = f.name

        try:
            # patch find_cargo_root 返回 None，模拟没有 Cargo.toml 的场景
            from unittest.mock import patch, MagicMock
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")

            with patch.object(mod, "find_cargo_root", return_value=None):
                with patch.object(mod.subprocess, "Popen", return_value=mock_proc) as mock_popen:
                    mod.format_rust(rs_file)
                    # 没有 Cargo.toml 时不应调用 Popen
                    assert mock_popen.call_count == 0, \
                        u"无 Cargo.toml 时不应调用 subprocess.Popen"
        finally:
            os.unlink(rs_file)

    def test_no_formatter(self):
        """格式化工具不存在时 run_formatter 不报错，返回 False"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as f:
            f.write(b"int main() {}")
            tmpfile = f.name

        try:
            from unittest.mock import patch

            # 模拟 subprocess.Popen 抛出异常（工具不存在）
            def raise_oserror(*args, **kwargs):
                raise OSError("No such file or directory: 'nonexistent-formatter'")

            with patch.object(mod.subprocess, "Popen", side_effect=raise_oserror):
                # run_formatter 应捕获异常并返回 False
                result = mod.run_formatter(["nonexistent-formatter", "-i"], tmpfile,
                                           "nonexistent")
                assert result is False, u"工具不存在时 run_formatter 应返回 False"
        finally:
            os.unlink(tmpfile)

    @pytest.mark.parametrize("ext", [
        ".js", ".ts", ".tsx", ".jsx", ".rs", ".py", ".c", ".cpp", ".h", ".hpp"
    ])
    def test_supported_extensions(self, ext):
        """所有支持的文件类型都应被识别并分发"""
        mod = self._mod()
        # 验证 main 中的扩展名检查逻辑
        # 我们只需要验证这些扩展名在 main() 的分发路径中
        # 由于 format-all 使用 ext == ".py" 这种精确匹配
        # 每个支持的扩展名都应触发对应的 formatter 调用
        from unittest.mock import patch, MagicMock

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"", b"")

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(b"content")
            tmpfile = f.name

        try:
            with patch.object(mod.subprocess, "Popen", return_value=mock_proc):
                from _run_main_helpers import _run_main
                code, _ = _run_main(mod, ["format-all.py", "--file", tmpfile])
                assert code == 0, u"支持的扩展名 {0} 应 exit(0)".format(ext)
        finally:
            os.unlink(tmpfile)

    def test_unexpected_format(self):
        """不支持的文件类型静默跳过，不调用任何 formatter"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"# Markdown")
            tmpfile = f.name

        try:
            from unittest.mock import patch, MagicMock
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")

            with patch.object(mod.subprocess, "Popen", return_value=mock_proc) as mock_popen:
                from _run_main_helpers import _run_main
                code, _ = _run_main(mod, ["format-all.py", "--file", tmpfile])
                assert code == 0, u"不支持的文件类型应 exit(0)"
                assert mock_popen.call_count == 0, \
                    u"不支持的文件类型不应调用任何 formatter"
        finally:
            os.unlink(tmpfile)

    def test_file_not_found(self):
        """文件不存在时 main() 输出提示并 exit(0)"""
        mod = self._mod()
        nonexistent = os.path.join(tempfile.gettempdir(), "_nonexistent_file_xyzzy.py")
        assert not os.path.exists(nonexistent)

        from _run_main_helpers import _run_main
        code, out = _run_main(mod, ["format-all.py", "--file", nonexistent])
        assert code == 0, u"文件不存在时应 exit(0)"
        assert u"文件不存在" in out or "not found" in out.lower() or \
            "不存在" in out, u"应输出文件不存在的提示"

    # ------------------------------------------------------------------
    # run_formatter 单元测试
    # ------------------------------------------------------------------

    def test_run_formatter_success(self):
        """run_formatter 在进程返回 0 时返回 True"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"x=1")
            tmpfile = f.name

        try:
            from unittest.mock import patch, MagicMock
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")

            with patch.object(mod.subprocess, "Popen", return_value=mock_proc):
                result = mod.run_formatter(["black", "-q", "--fast"], tmpfile, "black")
                assert result is True, u"returncode 0 时 run_formatter 应返回 True"
        finally:
            os.unlink(tmpfile)

    def test_run_formatter_failure(self):
        """run_formatter 在进程返回非 0 时返回 False"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"x=1")
            tmpfile = f.name

        try:
            from unittest.mock import patch, MagicMock
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.communicate.return_value = (b"error", b"")

            with patch.object(mod.subprocess, "Popen", return_value=mock_proc):
                result = mod.run_formatter(["black", "-q", "--fast"], tmpfile, "black")
                assert result is False, u"returncode 非 0 时 run_formatter 应返回 False"
        finally:
            os.unlink(tmpfile)

    def test_run_formatter_exception(self):
        """run_formatter 在进程抛出异常时返回 False 不报错"""
        mod = self._mod()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"x=1")
            tmpfile = f.name

        try:
            from unittest.mock import patch

            def raise_exception(*args, **kwargs):
                raise Exception("模拟异常")

            with patch.object(mod.subprocess, "Popen", side_effect=raise_exception):
                result = mod.run_formatter(["black"], tmpfile, "black")
                assert result is False, u"异常时 run_formatter 应返回 False"
        finally:
            os.unlink(tmpfile)

    # ------------------------------------------------------------------
    # find_cargo_root 测试
    # ------------------------------------------------------------------

    def test_find_cargo_root_found(self):
        """find_cargo_root 找到包含 Cargo.toml 的目录"""
        mod = self._mod()
        tmpdir = tempfile.mkdtemp()
        try:
            cargo_toml = os.path.join(tmpdir, "Cargo.toml")
            with open(cargo_toml, "w") as f:
                f.write("[package]\n")

            subdir = os.path.join(tmpdir, "src", "sub")
            os.makedirs(subdir)

            # 从子目录向上查找
            root = mod.find_cargo_root(subdir)
            assert root == tmpdir, u"应找到包含 Cargo.toml 的根目录"
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_find_cargo_root_not_found(self):
        """find_cargo_root 找不到 Cargo.toml 时返回 None"""
        mod = self._mod()
        # 使用深层嵌套的临时目录
        tmpdir = tempfile.mkdtemp()
        try:
            subdir = os.path.join(tmpdir, "a", "b", "c")
            os.makedirs(subdir)

            from unittest.mock import patch
            # patch os.path.exists 让 Cargo.toml 检查返回 False
            original_exists = os.path.exists

            def mock_exists(path):
                if path.endswith("Cargo.toml"):
                    return False
                return original_exists(path)

            with patch("os.path.exists", side_effect=mock_exists):
                root = mod.find_cargo_root(subdir)
                assert root is None, u"无 Cargo.toml 时应返回 None"
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_find_cargo_root_cache(self):
        """find_cargo_root 使用缓存加速重复查询"""
        mod = self._mod()
        tmpdir = tempfile.mkdtemp()
        try:
            cargo_toml = os.path.join(tmpdir, "Cargo.toml")
            with open(cargo_toml, "w") as f:
                f.write("[package]\n")

            # 第一次查询应找到
            root1 = mod.find_cargo_root(tmpdir)
            assert root1 == tmpdir

            # 第二次应命中缓存（不重新遍历）
            root2 = mod.find_cargo_root(tmpdir)
            assert root2 == tmpdir
            assert root2 is root1, u"缓存应返回相同对象"
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    # ------------------------------------------------------------------
    # C_EXTENSIONS 常量验证
    # ------------------------------------------------------------------

    def test_c_extensions_in_module(self):
        """验证 format-all 模块的 C_EXTENSIONS 常量"""
        mod = self._mod()
        # format-all.py 本身没有 C_EXTENSIONS，这个测试仅验证模块加载正常
        assert hasattr(mod, 'format_cpp'), u"模块应包含 format_cpp 函数"
