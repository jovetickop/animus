#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
#
# session-catchup.py — /clear 后恢复会话上下文
#
# 用法:
#   python session-catchup.py [--project-dir <路径>] [--session-dir <路径>]
#
# 扫描 Claude Code session JSONL 文件，找出最近的 features.json 写入事件
# 和进行中的任务，输出恢复报告。

from __future__ import print_function
import glob
import io
import json
import os
import sys

# Windows 下修复 stdout 编码，确保中文正常输出
try:
    # 优先通过环境变量确保 UTF-8 输出
    if "PYTHONIOENCODING" not in os.environ:
        os.environ["PYTHONIOENCODING"] = "utf-8"
except Exception:
    pass

if sys.version_info[0] < 3:
    try:
        reload(sys)
        sys.setdefaultencoding("utf-8")
    except NameError:
        pass
else:
    # Python 3: 直接设置 stdout 编码
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass


# ---------- 兼容层 ----------

def text_type():
    """兼容 Python 2/3 的字符串类型判断"""
    if sys.version_info[0] < 3:
        return (str, unicode)
    return (str,)


def safe_json_parse(line):
    """安全解析 JSON 行，兼容各种编码问题"""
    try:
        return json.loads(line)
    except (ValueError, TypeError):
        return None


# ---------- 路径处理 ----------

def get_projects_dir():
    """获取 Claude Code 项目会话数据目录。

    优先检测 ~/.claude/projects（当前版本），
    回退 ~/claude/projects（早期版本）。
    """
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".claude", "projects"),
        os.path.join(home, "claude", "projects"),
    ]
    for d in candidates:
        if os.path.isdir(d):
            return d
    # 都不存在时默认用第一个
    return candidates[0]


def sanitize_path(path):
    """将文件系统路径转换为 Claude Code 使用的 session 目录名。

    Claude Code 的路径 sanitize 规则：每个特殊字符替换为单个 `-`。
    - `:`, `\\`, `/`, `.` 都替换为 `-`
    - 相邻的特殊字符自然产生 `--`

    例如：C:\\Users\\11212\\.claude\\skills\\harness-cc
       → C--Users-11212--claude-skills-harness-cc
    """
    result = []
    for ch in path:
        if ch in (":", "\\", "/", "."):
            result.append("-")
        else:
            result.append(ch)
    return "".join(result)


def resolve_session_dir(project_dir):
    """根据项目路径确定 session 目录路径。

    返回 (session_dir_path, project_name)
    """
    projects_dir = get_projects_dir()

    # 如果提供了完整的项目路径，先 sanitize
    sanitized = sanitize_path(project_dir)
    session_dir = os.path.join(projects_dir, sanitized)

    if os.path.isdir(session_dir):
        return session_dir, sanitized

    # 精确匹配失败，返回构建的路径（即使目录不存在）
    return session_dir, sanitized


# ---------- session 文件扫描 ----------

def get_session_files(session_dir):
    """获取 session 目录下所有 JSONL 文件，按修改时间降序排列。"""
    if not os.path.isdir(session_dir):
        return []
    pattern = os.path.join(session_dir, "*.jsonl")
    files = glob.glob(pattern)
    # 按修改时间降序：最新的在前
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    return files


def parse_session_file(filepath):
    """解析单个 session JSONL 文件，提取关键信息。

    返回 dict:
      - session_id: session UUID
      - file_path: 文件路径
      - file_mtime: 文件修改时间
      - title: session 标题（ai-title 事件）
      - last_user_prompts: 最近的用户消息列表
      - features_writes: features.json 写入事件列表
      - has_last_prompt: 是否有 last-prompt 标记
    """
    result = {
        "session_id": None,
        "file_path": filepath,
        "file_mtime": os.path.getmtime(filepath),
        "title": "",
        "last_user_prompts": [],
        "features_writes": [],
        "has_last_prompt": False,
    }

    # session JSONL 文件通常是 UTF-8 编码，但 Windows 下 open() 默认用 GBK
    # 因此使用 io.open 指定编码读取
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"]
    file_content = None
    for enc in encodings:
        try:
            with io.open(filepath, "r", encoding=enc) as f:
                file_content = f.read()
            break
        except (UnicodeDecodeError, IOError):
            continue

    if file_content is None:
        # 所有编码都失败，尝试以二进制方式读取并忽略错误
        try:
            with io.open(filepath, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()
        except (IOError, OSError):
            return result

    try:
        for line in file_content.splitlines():
            d = safe_json_parse(line)
            if d is None:
                continue

            # 记录 session ID
            sid = d.get("sessionId")
            if sid and not result["session_id"]:
                result["session_id"] = sid

            # 记录 session 标题
            if d.get("type") == "ai-title":
                result["title"] = d.get("title", "")

            # 标记 last-prompt（表示 session 被 /clear 过或已压缩）
            if d.get("type") == "last-prompt":
                result["has_last_prompt"] = True

            # 提取用户消息
            if d.get("type") == "user":
                msg = d.get("message", {})
                content = msg.get("content", "")
                if content and not d.get("isMeta"):
                    # content 可能是字符串或列表（工具结果等）
                    if isinstance(content, list):
                        # 列表类型的消息，提取文本片段
                        texts = []
                        for item in content:
                            if isinstance(item, dict):
                                txt = item.get("text", item.get("content", ""))
                                if isinstance(txt, text_type()):
                                    texts.append(txt)
                        content = " ".join(texts)
                    # 截取前 200 字符显示
                    result["last_user_prompts"].append(content[:200])

            # 查找 features.json 写入事件（Write/Edit 工具调用）
            if d.get("type") == "tool_use":
                tu = d.get("tool_use", {})
                name = tu.get("name", "")
                if name in ("Write", "Edit", "WriteIfNotExists"):
                    inp = tu.get("input", {})
                    fp = inp.get("file_path", "")
                    if "features.json" in fp:
                        result["features_writes"].append({
                            "tool": name,
                            "file_path": fp,
                            "timestamp": d.get("timestamp", ""),
                        })

            # 查找 features.json 在 tool_result 中的输出信息
            if d.get("type") == "tool_result":
                content = d.get("content", "")
                if isinstance(content, text_type()) and "features.json" in content:
                    result["features_writes"].append({
                        "tool": "tool_result",
                        "content_snippet": content[:200],
                        "timestamp": d.get("timestamp", ""),
                    })

        # 保留最近的 5 条用户消息
        result["last_user_prompts"] = result["last_user_prompts"][-5:]

    except (IOError, OSError):
        # 文件无法读取，跳过
        pass

    return result


def format_timestamp(ts):
    """格式化时间戳为可读形式（兼容字符串和数字类型）。"""
    if ts is None:
        return ""
    if isinstance(ts, (int, float)):
        # 数字时间戳，转为可读日期
        import datetime
        try:
            dt = datetime.datetime.fromtimestamp(ts)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return str(ts)
    if isinstance(ts, text_type()):
        return ts.replace("T", " ").split(".")[0]
    return str(ts)


def get_session_title(session_dir, session_id):
    """尝试从 session 目录的 meta 信息获取标题"""
    meta_file = os.path.join(session_dir, session_id, "session.meta.json")
    if os.path.isfile(meta_file):
        try:
            with open(meta_file, "rb") as f:
                meta = json.load(f)
            return meta.get("title", "")
        except (IOError, ValueError):
            pass
    return ""


# ---------- 恢复报告 ----------

def print_recovery_report(session_dir, sessions_info, features_writes_per_session):
    """打印恢复报告。"""
    print("=" * 60)
    print(u"   Claude Code 会话恢复报告")
    print("=" * 60)
    print()

    project_name = os.path.basename(session_dir)
    print(u"  项目: {0}".format(project_name))
    print(u"  数据目录: {0}".format(session_dir))
    print()

    if not sessions_info:
        print(u"  [信息] 未找到任何 session 文件。")
        print(u"  [信息] 这是新项目，或 session 已被清理。")
        print()
        print("=" * 60)
        return

    # 显示最近 session 概览
    active_session = sessions_info[0]  # 最新 session
    is_active = active_session["session_id"] is not None

    print(u"  最近活动 session:")
    print(u"    UUID: {0}".format(active_session["session_id"] or "unknown"))
    print(u"    文件: {0}".format(os.path.basename(active_session["file_path"])))
    print(u"    最后活动: {0}".format(
        format_timestamp(active_session.get("file_mtime", 0))
    ))
    if active_session["title"]:
        print(u"    标题: {0}".format(active_session["title"]))
    if active_session["has_last_prompt"]:
        print(u"    状态: 已标记 last-prompt（可能已被 /clear 或已压缩）")
    print()

    # 显示最近用户消息
    if active_session["last_user_prompts"]:
        print(u"  最近用户消息:")
        for i, msg in enumerate(active_session["last_user_prompts"], 1):
            # 清理消息中的换行
            clean = msg.replace("\n", " ").replace("\r", "")
            if len(clean) > 120:
                clean = clean[:117] + "..."
            print(u"    {0}. {1}".format(i, clean))
        print()

    # 显示 features.json 写入活动
    all_features_writes = features_writes_per_session.get(
        active_session["session_id"], []
    )
    # 也检查其他 session 的 features 写入
    for sid, writes in features_writes_per_session.items():
        if sid != active_session["session_id"] and writes:
            all_features_writes.extend(writes)

    if all_features_writes:
        # 按时间排序
        all_features_writes.sort(
            key=lambda w: w.get("timestamp", ""), reverse=True
        )
        print(u"  features.json 相关事件:")
        for w in all_features_writes[:5]:
            ts = format_timestamp(w.get("timestamp", ""))
            tool = w.get("tool", "")
            fp = w.get("file_path", w.get("content_snippet", ""))
            print(u"    [{0}] {1} — {2}".format(ts, tool, fp[:120]))
        print()

    # 检查当前 features.json 中的任务状态
    state_dir = os.path.join(os.path.dirname(session_dir), "..", "state")
    # 统一路径：features.json 固定在 .claude/state/
    features_candidates = [
        os.path.join(os.path.dirname(session_dir), "..", "state", "features.json"),
    ]

    features_found = None
    for cand in features_candidates:
        real = os.path.normpath(cand)
        if os.path.isfile(real):
            features_found = real
            break

    if features_found:
        print(u"  当前任务状态 ({0}):".format(
            os.path.relpath(features_found, os.path.dirname(session_dir))
        ))
        try:
            with open(features_found, "rb") as f:
                data = json.load(f)
            tasks = []
            if isinstance(data, dict):
                tasks = data.get("initial_tasks", data.get("tasks", []))
            elif isinstance(data, list):
                tasks = data

            in_progress = [t for t in tasks if t.get("status") == "in_progress"]
            failed = [t for t in tasks if t.get("status") == "failed"]
            pending = [t for t in tasks if t.get("status") == "pending"]
            passed = [t for t in tasks if t.get("status") == "passed"]

            print(u"    总任务: {0}  |  通过: {1}  |  失败: {2}  |  进行中: {3}  |  待处理: {4}".format(
                len(tasks), len(passed), len(failed), len(in_progress), len(pending)
            ))

            if in_progress:
                for t in in_progress:
                    print(u"    ➤ 进行中: {0} — {1}".format(
                        t.get("id", "?"), t.get("name", "")
                    ))
            if failed:
                for t in failed[:3]:
                    print(u"    ✗ 失败:   {0} — {1}".format(
                        t.get("id", "?"), t.get("name", "")
                    ))
                    err = t.get("last_error", "")
                    if err:
                        print(u"      原因: {0}".format(str(err)[:150]))
        except (IOError, ValueError):
            print(u"    [无法解析 features.json]")
    else:
        print(u"  [提示] 当前未找到 features.json，项目可能尚未初始化。")
    print()

    # 显示历史 session 概览
    if len(sessions_info) > 1:
        print(u"  历史 session（最近 {0} 个）:".format(len(sessions_info) - 1))
        for s in sessions_info[1:]:
            title = s["title"] or "(无标题)"
            sid = s["session_id"] or "unknown"
            mtime = format_timestamp(s.get("file_mtime", 0))
            prompts = len(s["last_user_prompts"])
            print(u"    {0}  {1}  [{2}]  ({3} 条消息)".format(
                sid[:8], mtime, title[:40], prompts
            ))
        print()

    print(u"  恢复建议:")
    print(u"    1. 如需继续之前的工作，请查看上方 '最近用户消息' 中的上下文。")
    print(u"    2. 检查 '当前任务状态' 了解未完成的任务。")
    print(u"    3. 失败的 task 需要手动修复或重新执行。")
    print("=" * 60)


# ---------- 主入口 ----------

def main():
    """主函数：扫描 session 并输出恢复报告。"""
    # 解析命令行参数
    project_dir = None
    session_dir_arg = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--project-dir" and i + 1 < len(args):
            project_dir = args[i + 1]
            i += 2
        elif args[i] == "--session-dir" and i + 1 < len(args):
            session_dir_arg = args[i + 1]
            i += 2
        else:
            i += 1

    # 确定 session 目录
    if session_dir_arg:
        # 直接指定了 session 目录
        session_dir = session_dir_arg
        project_name = os.path.basename(session_dir)
    elif project_dir:
        session_dir, project_name = resolve_session_dir(project_dir)
    else:
        # 尝试自动检测：使用当前工作目录
        cwd = os.getcwd()
        session_dir, project_name = resolve_session_dir(cwd)

    # 获取 session 文件
    session_files = get_session_files(session_dir)

    # 解析所有 session
    sessions_info = []
    features_writes_per_session = {}

    for fp in session_files:
        info = parse_session_file(fp)
        sid = info["session_id"]
        if sid:
            sessions_info.append(info)
            features_writes_per_session[sid] = info["features_writes"]

    # 输出恢复报告
    print_recovery_report(session_dir, sessions_info, features_writes_per_session)

    return 0


if __name__ == "__main__":
    sys.exit(main())
