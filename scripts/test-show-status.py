#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
# animus show-status.py 功能测试

from __future__ import print_function, unicode_literals
import json
import os
import subprocess
import sys
import tempfile


PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(u"  [PASS] {0}".format(name))
    else:
        FAIL += 1
        msg = u"  [FAIL] {0}".format(name)
        if detail:
            msg += u" - {0}".format(detail)
        print(msg)


def read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        return json.loads(f.read())


def make_features(tmpdir, tasks):
    """创建临时 features.json 并返回路径。"""
    path = os.path.join(tmpdir, "features.json")
    data = {"initial_tasks": tasks}
    with open(path, "wb") as f:
        f.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    return path, os.path.dirname(path)


def run_status(state_dir, arg=""):
    """运行 show-status.py 并返回输出。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "..", "templates", "animus", "show-status.py")
    cmd = [sys.executable, script_path, state_dir]
    if arg:
        cmd.append(arg)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace"), proc.returncode
    except Exception as e:
        return "", str(e), -1


def main():
    global PASS, FAIL
    print(u"=" * 60)
    print(u"show-status.py 功能测试")
    print(u"=" * 60)

    # ============================================================
    # 测试数据：模拟多任务依赖场景
    # ============================================================
    tasks = [
        {"id": "T001", "name": "项目初始化", "status": "passed", "depends_on": [], "priority": 1, "last_error": "", "updated_at": "2026-07-01"},
        {"id": "T002", "name": "配置数据库", "status": "passed", "depends_on": ["T001"], "priority": 2, "last_error": "", "updated_at": "2026-07-02"},
        {"id": "T003", "name": "实现登录", "status": "in_progress", "depends_on": ["T002"], "priority": 3, "last_error": "", "updated_at": "2026-07-03"},
        {"id": "T004", "name": "实现注册", "status": "pending", "depends_on": ["T003"], "priority": 3, "last_error": "", "updated_at": ""},
        {"id": "T005", "name": "实现密码重置", "status": "pending", "depends_on": ["T003"], "priority": 2, "last_error": "", "updated_at": ""},
        {"id": "T006", "name": "单元测试", "status": "pending", "depends_on": ["T004", "T005"], "priority": 4, "last_error": "", "updated_at": ""},
        {"id": "T007", "name": "部署文档", "status": "pending", "depends_on": [], "priority": 1, "last_error": "", "updated_at": ""},
    ]

    tmpdir = tempfile.mkdtemp(prefix="animus_test_")
    features_path, state_dir = make_features(tmpdir, tasks)
    test(u"测试环境准备完成", os.path.exists(features_path))

    # ============================================================
    # 测试 1: --json 输出
    # ============================================================
    print(u"\n--- 测试 1: --json 输出格式 ---")
    out, err, code = run_status(state_dir, "--json")
    test(u"退出码为 0", code == 0, u"实际: {0}".format(code))
    test(u"输出不为空", len(out) > 0)
    try:
        parsed = json.loads(out)
        test(u"输出为合法 JSON", True)
        test(u"JSON 包含 total 字段", "total" in parsed, u"字段: {0}".format(list(parsed.keys())))
        test(u"total 值正确", parsed.get("total") == 7, u"实际: {0}".format(parsed.get("total")))
        test(u"JSON 包含 passed 字段", "passed" in parsed)
        test(u"passed 值正确", parsed.get("passed") == 2, u"实际: {0}".format(parsed.get("passed")))
        test(u"JSON 包含 failed 字段", "failed" in parsed)
        test(u"failed 值正确", parsed.get("failed") == 0, u"实际: {0}".format(parsed.get("failed")))
        test(u"JSON 包含 in_progress 字段", "in_progress" in parsed)
        test(u"in_progress 值正确", parsed.get("in_progress") == 1, u"实际: {0}".format(parsed.get("in_progress")))
        test(u"JSON 包含 pending 字段", "pending" in parsed)
        test(u"pending 值正确", parsed.get("pending") == 4, u"实际: {0}".format(parsed.get("pending")))
        test(u"JSON 包含 progress_pct 字段", "progress_pct" in parsed)
        test(u"progress_pct 值正确", parsed.get("progress_pct") == 28, u"实际: {0}".format(parsed.get("progress_pct")))
        test(u"JSON 包含 status 字段", "status" in parsed)
        test(u"状态为 in_progress", parsed.get("status") == "in_progress", u"实际: {0}".format(parsed.get("status")))
        test(u"JSON 包含 block_chains 字段", "block_chains" in parsed)
        test(u"JSON 包含 tasks 数组", "tasks" in parsed and isinstance(parsed["tasks"], list))
    except ValueError as e:
        test(u"输出为合法 JSON", False, u"解析失败: {0}".format(e))

    # ============================================================
    # 测试 2: --summary 输出
    # ============================================================
    print(u"\n--- 测试 2: --summary 输出 ---")
    out, err, code = run_status(state_dir, "--summary")
    test(u"退出码为 0", code == 0, u"实际: {0}".format(code))
    test(u"输出包含进度信息", "进度" in out or "progress" in out.lower(), u"实际输出前200字: {0}".format(out[:200]))
    test(u"输出不包含依赖树标记", "依赖树" not in out, u"--summary 应只显示摘要不显示树")

    # ============================================================
    # 测试 3: --tree 输出
    # ============================================================
    print(u"\n--- 测试 3: --tree 输出 ---")
    out, err, code = run_status(state_dir, "--tree")
    test(u"退出码为 0", code == 0, u"实际: {0}".format(code))
    test(u"输出包含依赖树标记", "├" in out or "└" in out, u"--tree 应显示树")
    test(u"输出不包含看板头部", "╔" not in out, u"--tree 不应显示看板边框")
    test(u"树中包含 T001", "T001" in out)
    test(u"树中包含 T003", "T003" in out)
    test(u"树中包含 T007", "T007" in out)

    # ============================================================
    # 测试 4: 默认输出（完整看板）
    # ============================================================
    print(u"\n--- 测试 4: 默认输出（完整看板）---")
    out, err, code = run_status(state_dir)
    test(u"退出码为 0", code == 0, u"实际: {0}".format(code))
    test(u"输出包含看板边框", "╔" in out, u"默认输出应有头部边框")
    test(u"输出包含进度信息", "进度" in out)
    test(u"输出包含依赖树结构", "├" in out or "└" in out, u"默认输出应有树结构")

    # ============================================================
    # 测试 5: 空任务列表
    # ============================================================
    print(u"\n--- 测试 5: 空任务列表 ---")
    empty_tasks = []
    _, empty_dir = make_features(tmpdir, empty_tasks)
    out, err, code = run_status(empty_dir, "--json")
    test(u"空列表 --json 退出码为 0", code == 0, u"实际: {0}".format(code))

    # ============================================================
    # 测试 6: 无 features.json 的错误处理
    # ============================================================
    print(u"\n--- 测试 6: 无 features.json 错误处理 ---")
    nofile_dir = os.path.join(tmpdir, "nope")
    os.makedirs(nofile_dir, exist_ok=True)
    out, err, code = run_status(nofile_dir)
    test(u"无文件时退出码为 1", code == 1, u"实际: {0}".format(code))
    test(u"友好提示包含 features.json 信息", "未找到" in out or "features.json" in out, u"应提示 features.json 未找到")

    # ============================================================
    # 测试 7: 失败任务场景
    # ============================================================
    print(u"\n--- 测试 7: 失败任务场景 ---")
    failed_tasks = [
        {"id": "F001", "name": "失败任务", "status": "failed", "depends_on": [], "priority": 1, "last_error": "网络超时", "updated_at": "2026-07-04"},
        {"id": "F002", "name": "正常任务", "status": "passed", "depends_on": [], "priority": 2, "last_error": "", "updated_at": "2026-07-04"},
    ]
    _, fail_dir = make_features(tmpdir, failed_tasks)
    out, err, code = run_status(fail_dir, "--json")
    test(u"失败场景退出码为 0", code == 0)
    try:
        parsed = json.loads(out)
        test(u"JSON 中 failed 值正确", parsed.get("failed") == 1, u"实际: {0}".format(parsed.get("failed")))
        test(u"状态为 failed", parsed.get("status") == "failed", u"实际: {0}".format(parsed.get("status")))
    except ValueError:
        test(u"JSON 解析成功", False)

    # ============================================================
    # 汇总
    # ============================================================
    print(u"\n" + "=" * 60)
    total = PASS + FAIL
    print(u"测试完成: {0}/{1} 通过, {2} 失败".format(PASS, total, FAIL))
    if FAIL > 0:
        print(u"存在失败的测试用例")
        sys.exit(1)
    else:
        print(u"全部通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()
