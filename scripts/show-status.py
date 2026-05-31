#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
# harness-cc 状态显示工具 —— 增强版（含持续时间、预测、失败趋势）

from __future__ import print_function, unicode_literals
import datetime
import json
import os
import sys


def read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        return json.loads(f.read())


def read_jsonl_lines(path):
    """读取 JSONL 文件，返回解析后的记录列表"""
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "rb") as f:
        for raw_line in f:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                pass
    return records


def get_priority(task):
    """获取任务优先级"""
    value = task.get("priority", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_depends_on(task):
    """获取任务的依赖列表"""
    depends_on = task.get("depends_on", [])
    if isinstance(depends_on, list):
        return [str(item) for item in depends_on if str(item).strip()]
    return []


def can_run(task, status_by_id):
    """检查任务的所有依赖是否已通过"""
    for dep_id in get_depends_on(task):
        if status_by_id.get(dep_id) != "passed":
            return False
    return True


def get_tasks(data):
    """从 features.json 中提取任务列表，支持新旧两种格式"""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "initial_tasks" in data:
            return data["initial_tasks"]
        if "tasks" in data:
            return data["tasks"]
    return []


def parse_iso_time(time_str):
    """解析 ISO 格式时间字符串为 datetime 对象"""
    if not time_str:
        return None
    # 支持的格式: "2024-01-15T10:30:00Z", "2024-01-15 10:30:00"
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(str(time_str)[:19], fmt)
        except ValueError:
            continue
    return None


def get_duration_minutes(created_str, updated_str=None):
    """
    计算任务持续时间。
    如果提供了 updated_str，计算 created -> updated 的时长。
    否则计算 created -> now 的时长。
    返回分钟数，如果无法计算则返回 None。
    """
    if not created_str:
        return None
    created = parse_iso_time(created_str)
    if not created:
        return None

    # 获取当前 UTC 时间，兼容 Python 2/3
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    except AttributeError:
        now_utc = datetime.datetime.utcnow()

    if updated_str:
        end = parse_iso_time(updated_str)
        if not end:
            end = now_utc
    else:
        end = now_utc
    delta = end - created
    return int(delta.total_seconds() / 60)


def format_duration(minutes):
    """将分钟数格式化为可读字符串"""
    if minutes is None:
        return u"未知"
    if minutes < 60:
        return u"{0} 分钟".format(minutes)
    hours = minutes / 60
    mins = minutes % 60
    if mins == 0:
        return u"{0} 小时".format(hours)
    return u"{0} 小时 {1} 分钟".format(hours, mins)


def get_recent_failures(history_records, count=5):
    """获取最近的失败记录"""
    failures = [r for r in history_records if r.get("to") == "failed"]
    return failures[-count:]


def summarize_failure_trend(history_records):
    """
    分析失败趋势。
    返回每个任务最近的失败次数摘要。
    """
    if not history_records:
        return {}
    # 按任务统计最近的失败
    task_fails = {}
    for record in history_records:
        if record.get("to") == "failed":
            tid = record.get("task_id", "unknown")
            task_fails.setdefault(tid, []).append(record)
    # 汇总
    summary = {}
    for tid, fails in task_fails.items():
        summary[tid] = {
            "total": len(fails),
            "latest": fails[-1].get("timestamp", ""),
            "latest_message": fails[-1].get("message", "")
        }
    return summary


def main():
    # P1-5: 支持 --archive 标志显示已归档任务
    show_archive = "--archive" in sys.argv
    # 过滤掉 --archive 参数后，第一个非选项参数作为 state_root
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        state_root = args[0]
    else:
        # 自动检测 state 目录
        default_root = os.path.join(".claude", "state")
        if os.path.exists(default_root):
            state_root = default_root
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            state_root = os.path.join(script_dir, "..", "state")

    # P1-5: 优先使用 features.active.json，向后兼容 features.json
    active_path = os.path.join(state_root, "features.active.json")
    legacy_path = os.path.join(state_root, "features.json")
    archive_path = os.path.join(state_root, "features.archive.json")
    history_path = os.path.join(state_root, "harness-history.jsonl")

    if show_archive:
        # 显示已归档任务
        if not os.path.exists(archive_path):
            print(u"未找到 features.archive.json: {0}".format(archive_path))
            return 0
        data = read_json(archive_path)
        tasks = get_tasks(data)
        print(u"=== 已归档任务 (features.archive.json) ===")
        print(u"")
        if not tasks:
            print(u"(无已归档任务)")
            return 0
        print(u"归档任务数: {0}".format(len(tasks)))
        for t in tasks:
            tid = t.get("id", "?")
            name = t.get("name", "")
            status = t.get("status", "")
            updated = t.get("updated_at", "")
            print(u"  {0} | {1} | {2} | {3}".format(tid, status, name, updated))
        return 0

    # 显示 active 任务
    features_path = active_path if os.path.exists(active_path) else legacy_path
    if not os.path.exists(features_path):
        print(u"未找到状态文件: {0}".format(features_path))
        return 1

    # ============================================================
    # 读取 active 任务文件
    # ============================================================
    data = read_json(features_path)
    tasks = get_tasks(data)

    # 创建 status_by_id 映射
    status_by_id = {str(task.get("id", "")): str(task.get("status", "")) for task in tasks}

    # ============================================================
    # 统计信息
    # ============================================================
    total = len(tasks)
    passed = sum(1 for t in tasks if t.get("status") == "passed")
    completed = sum(1 for t in tasks if t.get("status") == "completed")
    passed_total = passed + completed
    failed_tasks = [t for t in tasks if t.get("status") == "failed"]
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]

    # 当前 in_progress 任务
    in_progress = None
    for t in tasks:
        if t.get("status") == "in_progress":
            in_progress = t
            break

    # 可执行的 pending 任务
    executable_pending = [t for t in pending_tasks if can_run(t, status_by_id)]
    executable_pending.sort(key=lambda t: (-get_priority(t), str(t.get("id", ""))))
    next_pending = executable_pending[0] if executable_pending else None

    # ============================================================
    # 显示 Oracle 验证门配置状态
    # ============================================================
    verify_config = data.get("verify_config") if isinstance(data, dict) else None
    if verify_config:
        enabled = verify_config.get("verify_enabled", False)
        cmd = verify_config.get("verify_command", "")
        timeout = verify_config.get("verify_timeout_seconds", 120)
        status_text = u"已启用" if enabled else u"未启用"
        cmd_text = cmd if cmd else u"(无)"
        print(u"Oracle 验证门: {0} | 命令: {1} | 超时: {2}s".format(status_text, cmd_text, timeout))

    print(u"")
    print(u"任务总数: {0}".format(total))
    print(u"已通过: {0}".format(passed_total))
    print(u"失败: {0}".format(len(failed_tasks)))
    print(u"待处理: {0}".format(len(pending_tasks)))

    # ============================================================
    # P2-5: 显示进行中任务及其持续时间
    # ============================================================
    if in_progress:
        task_id = in_progress.get("id", "UNKNOWN")
        task_name = in_progress.get("name", "")
        updated_at = in_progress.get("updated_at", "")

        # 任务持续时间（从 created_at 或 updated_at 算起）
        metadata = in_progress.get("metadata", {})
        created_at = metadata.get("created_at", "") if isinstance(metadata, dict) else ""
        duration = get_duration_minutes(created_at or updated_at)
        duration_text = format_duration(duration) if duration else u"未知"

        print(u"进行中: {0} {1} (持续 {2})".format(task_id, task_name, duration_text))
        if updated_at:
            print(u"  最后更新: {0}".format(updated_at))
    elif next_pending:
        task_id = next_pending.get("id", "UNKNOWN")
        task_name = next_pending.get("name", "")
        priority = get_priority(next_pending)
        print(u"下一个可执行任务: {0} {1} (priority={2})".format(task_id, task_name, priority))

        # P2-5: 预测剩余
        blocked = len(pending_tasks) - len(executable_pending)
        if blocked > 0:
            print(u"  被依赖阻塞: {0} 个任务".format(blocked))
            # 简单预测：按可执行任务数量估算
            if executable_pending:
                avg_minutes_per_task = 10  # 假设每任务平均 10 分钟
                est_minutes = len(executable_pending) * avg_minutes_per_task + blocked * avg_minutes_per_task * 1.5
                print(u"  预估剩余: ~{0}".format(format_duration(int(est_minutes))))
    else:
        print(u"所有任务均已完成。")

    # ============================================================
    # 显示失败任务
    # ============================================================
    if failed_tasks:
        failed_tasks.sort(key=lambda t: (-get_priority(t), str(t.get("id", ""))))
        top_failed = failed_tasks[0]
        err = str(top_failed.get("last_error", "")).strip()
        task_id = top_failed.get("id", "UNKNOWN")
        task_name = top_failed.get("name", "")
        print(u"待处理失败任务: {0} {1}".format(task_id, task_name))
        if err:
            print(u"  最近失败原因: {0}".format(err))

        # 列出所有失败任务
        if len(failed_tasks) > 1:
            print(u"  其他失败任务:")
            for ft in failed_tasks[1:]:
                print(u"    - {0} {1}".format(ft.get("id", "??"), ft.get("name", "")))

    # ============================================================
    # P2-5: 读取 harness-history.jsonl 显示失败趋势
    # ============================================================
    history_records = read_jsonl_lines(history_path)
    if history_records:
        # 最近 5 次失败
        recent_fails = get_recent_failures(history_records, 5)
        if recent_fails:
            print(u"")
            print(u"最近 {0} 次失败:".format(len(recent_fails)))
            for fail in recent_fails:
                tid = fail.get("task_id", "?")
                ts = fail.get("timestamp", "?")
                msg = fail.get("message", "")
                if len(msg) > 60:
                    msg = msg[:60] + "..."
                print(u"  - [{0}] {1}: {2}".format(ts, tid, msg))

        # 失败趋势汇总
        trend = summarize_failure_trend(history_records)
        multi_fail_tasks = {tid: info for tid, info in trend.items() if info["total"] >= 2}
        if multi_fail_tasks:
            print(u"")
            print(u"重复失败任务:")
            for tid, info in sorted(multi_fail_tasks.items()):
                print(u"  - {0}: 失败 {1} 次, 最近: {2}".format(
                    tid, info["total"], info["latest_message"][:50] if info["latest_message"] else info["latest"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
