#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
# archive-iteration.py — 迭代归档
# 打包当前运行时状态到 archive/iteration-N-<name>/ 目录，清空当前状态

from __future__ import print_function, unicode_literals
import io
import json
import os
import shutil
import sys
import datetime
import subprocess


def ensure_utf8():
    if "PYTHONIOENCODING" not in os.environ:
        os.environ["PYTHONIOENCODING"] = "utf-8"


def get_next_iteration_number(archive_dir):
    """读取 archive 目录，返回下一个迭代号。"""
    if not os.path.isdir(archive_dir):
        return 1
    max_num = 0
    for name in os.listdir(archive_dir):
        if name.startswith("iteration-"):
            try:
                num = int(name.split("-")[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                pass
    return max_num + 1


def get_git_stats(project_dir):
    """获取 git 统计（当前分支 vs 初始）。"""
    try:
        result = subprocess.Popen(
            ["git", "log", "--oneline", "--shortstat"],
            cwd=project_dir,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, _ = result.communicate()
        return stdout.decode("utf-8", errors="replace")[:500]
    except Exception:
        return "（无法获取 git 统计）"


def main():
    ensure_utf8()
    import argparse
    parser = argparse.ArgumentParser(description="迭代归档工具")
    parser.add_argument("--project-dir", default=".", help="项目根目录")
    parser.add_argument("--name", default="", help="迭代名称")
    parser.add_argument("--iter-num", type=int, default=0, help="迭代号（自动检测）")
    args = parser.parse_args()

    project_dir = args.project_dir
    harness_dir = os.path.join(project_dir, ".claude", "harness-cc")
    archive_dir = os.path.join(harness_dir, "archive")

    if not os.path.isdir(harness_dir):
        print("错误: .claude/harness-cc 目录不存在")
        return 1

    iter_num = args.iter_num if args.iter_num > 0 else get_next_iteration_number(archive_dir)
    iter_name = args.name if args.name else "unnamed"
    iter_dir_name = "iteration-{}-{}".format(iter_num, iter_name)
    iter_dir = os.path.join(archive_dir, iter_dir_name)

    # 创建归档目录（同名冲突时报错不覆盖）
    if os.path.isdir(iter_dir):
        print(u"错误: 归档目录已存在: {}".format(iter_dir))
        return 1
    os.makedirs(iter_dir)

    # 复制运行时文件
    files_to_archive = ["features.json", "harness-history.jsonl",
                        "feature-detail.md", "domain-lexicon.md",
                        "task_plan.md", "findings.md"]
    for fname in files_to_archive:
        src = os.path.join(harness_dir, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(iter_dir, fname))
            print(u"  归档: {}".format(fname))

    # 复制 docs 目录（报告等）
    docs_src = os.path.join(harness_dir, "docs")
    docs_dst = os.path.join(iter_dir, "docs")
    if os.path.isdir(docs_src):
        shutil.copytree(docs_src, docs_dst, dirs_exist_ok=True)
        print(u"  归档: docs/")

    # 生成总结
    git_stats = get_git_stats(project_dir)
    summary = u"""# 迭代总结 — {name}

- 迭代编号: {num}
- 归档时间: {time}

## 归档内容
- features.json
- harness-history.jsonl
- task_plan.md
- findings.md
- docs/

## Git 统计（近期变更）
```
{git_stats}
```
""".format(name=iter_name, num=iter_num,
           time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           git_stats=git_stats)

    with io.open(os.path.join(iter_dir, "iteration-summary.md"), "w", encoding="utf-8") as f:
        f.write(summary)
    print(u"  生成: iteration-summary.md")

    # 清理运行时残留（以下文件归档后删除运行时副本）
    for fname in ["plan-context.md", "domain-lexicon.md", "feature-detail.md"]:
        fpath = os.path.join(harness_dir, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
            print(u"  清理: {}".format(fname))

    # 清空当前状态
    for fname in files_to_archive:
        fpath = os.path.join(harness_dir, fname)
        if os.path.isfile(fpath):
            if fname == "features.json":
                # 清空 tasks
                with io.open(fpath, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data["tasks"] = []
                elif isinstance(data, list):
                    data = []
                with io.open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif fname == "harness-history.jsonl":
                with io.open(fpath, "w", encoding="utf-8") as f:
                    f.write("")
            elif fname == "task_plan.md":
                with io.open(fpath, "w", encoding="utf-8") as f:
                    f.write("# 任务计划\n\n## 子步骤\n\n")
            elif fname == "findings.md":
                with io.open(fpath, "w", encoding="utf-8") as f:
                    f.write(u"# 知识积累（迭代 I{num}）\n\n".format(num=iter_num + 1))
        print(u"  清空: {}".format(fname))

    print()
    print(u"迭代 {} 归档完成 → {}".format(iter_num, iter_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
