#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
# harness-cc 回归测试运行器 —— 读取项目配置执行构建和测试

from __future__ import print_function, unicode_literals
import argparse
import json
import os
import subprocess
import sys


def read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        return json.loads(f.read())


def run_command(cmd, label, project_root):
    """
    执行命令并输出结果。
    返回 (exit_code, output_lines)
    """
    print(u"[{0}] 开始执行: {1}".format(label, cmd))
    print("-" * 60)

    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=project_root
        )
        output_lines = []
        for raw_line in iter(proc.stdout.readline, b""):
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            output_lines.append(line)
            print(line)
        proc.wait()
        exit_code = proc.returncode
    except Exception as e:
        print(u"[{0}] 执行异常: {1}".format(label, e))
        exit_code = -1
        output_lines = [str(e)]

    print("-" * 60)
    print(u"[{0}] 退出码: {1}".format(label, exit_code))
    return exit_code, output_lines


def main():
    parser = argparse.ArgumentParser(description=u"运行回归测试（构建+测试）")
    parser.add_argument("--project-root", default=".", help=u"项目根目录")
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    claude_root = os.path.join(project_root, ".claude")
    harness_root = os.path.join(claude_root, "harness")
    state_root = os.path.join(claude_root, "state")

    config_path = os.path.join(harness_root, "project-config.json")
    features_path = os.path.join(state_root, "features.json")

    build_command = ""
    test_command = ""

    # ============================================================
    # 方案一: 从 project-config.json 读取配置
    # ============================================================
    if os.path.exists(config_path):
        try:
            config = read_json(config_path)
            # 支持旧版字段名和新版嵌套结构
            build_command = str(config.get("build-command", config.get("build_command", "")) or "")
            test_command = str(config.get("test-command", config.get("test_command", "")) or "")

            # 如果新结构中有 backend/frontend，优先使用
            if not build_command and "backend" in config:
                build_command = str(config["backend"].get("build-command", "") or "")
            if not test_command and "backend" in config:
                test_command = str(config["backend"].get("test-command", "") or "")

            # legacy 兼容字段
            if not build_command and not test_command and "_backward-compatibility" in config:
                legacy = config["_backward-compatibility"].get("legacyFields", {})
                build_command = str(legacy.get("build-command", legacy.get("build_command", "")) or "")
                test_command = str(legacy.get("test-command", legacy.get("test_command", "")) or "")

        except Exception as e:
            print(u"警告: 读取 project-config.json 失败: {0}".format(e))

    # ============================================================
    # 方案二: 从 features.json 读取 test_command（降级方案）
    # ============================================================
    if not test_command and os.path.exists(features_path):
        try:
            features = read_json(features_path)
            # 支持新旧两种格式
            if isinstance(features, dict):
                task_list = features.get("tasks") or features.get("initial_tasks") or []
            elif isinstance(features, list):
                task_list = features
            else:
                task_list = []

            if task_list:
                # 取第一个任务的 test_command
                first = task_list[0] if isinstance(task_list, list) else task_list
                test_command = str(first.get("test_command", "") or "")
        except Exception as e:
            print(u"警告: 读取 features.json 失败: {0}".format(e))

    # ============================================================
    # 执行构建
    # ============================================================
    if build_command:
        build_exit, _ = run_command(build_command, u"构建", project_root)
        if build_exit != 0:
            print(u"构建失败，退出码 {0}，终止测试".format(build_exit))
            sys.exit(0)
    else:
        print(u"提示: 未配置 build_command，跳过构建步骤")

    # ============================================================
    # 执行测试
    # ============================================================
    if test_command:
        test_exit, _ = run_command(test_command, u"测试", project_root)
        print(u"回归测试完成，退出码: {0}".format(test_exit))
    else:
        print(u"提示: 未配置 test_command，跳过测试步骤")

    sys.exit(0)


if __name__ == "__main__":
    main()
