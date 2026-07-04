#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
animus-engine.py — 统一 CLI 入口

用法：
    python animus-engine.py status
    python animus-engine.py transition <task_id> <to> [--evidence <text>]
    python animus-engine.py validate
    python animus-engine.py archive [--name <name>] [--discard]
    python animus-engine.py rebuild
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="animus-engine",
        description="Animus 状态机引擎统一 CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    sub.add_parser("status", help="显示任务状态")

    # transition
    p = sub.add_parser("transition", help="状态流转")
    p.add_argument("task_id", help="任务 ID")
    p.add_argument("to", choices=["pending", "in_progress", "passed", "failed", "completed"],
                   help="目标状态")
    p.add_argument("--evidence", default="", help="状态变更证据（如测试日志路径）")

    # validate
    p = sub.add_parser("validate", help="校验 features.json 结构")
    p.add_argument("--plugin", action="store_true", help="校验插件自身完整性（plugin-validator）")
    p.add_argument("--strict", action="store_true", help="CI 严格模式")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    p.add_argument("--fix", action="store_true", help="自动修复简单问题")

    # archive
    p = sub.add_parser("archive", help="归档当前迭代")
    p.add_argument("--name", default="", help="迭代名称")
    p.add_argument("--discard", action="store_true", help="丢弃未完成任务")

    # rebuild
    sub.add_parser("rebuild", help="从 memlog 重建 features.json")

    args = parser.parse_args()

    # dispatch
    try:
        if args.command == "status":
            from engine.cmd_status import run
            run()
        elif args.command == "transition":
            from engine.cmd_transition import run
            run(args.task_id, args.to, args.evidence)
        elif args.command == "validate":
            if getattr(args, "plugin", False):
                import subprocess
                cmd = [sys.executable,
                       os.path.join(os.path.dirname(__file__), "plugin-validator.py")]
                if args.strict:
                    cmd.append("--strict")
                if getattr(args, "json", False):
                    cmd.append("--json")
                if args.fix:
                    cmd.append("--fix")
                ret = subprocess.call(cmd)
                sys.exit(ret)
            else:
                from engine.cmd_validate import run
                run()
        elif args.command == "archive":
            from engine.cmd_archive import run
            run(args.name, args.discard)
        elif args.command == "rebuild":
            from engine.cmd_rebuild import run
            run()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
