#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
# harness-cc 任务进度更新脚本 —— 完整状态机 + 失败历史记录

from __future__ import print_function, unicode_literals
import argparse
import json
import os
import re
import subprocess
import sys
import time

# ============================================================
# 有效状态转换表
# 格式: from_status -> {允许的 to_status 集合}
# ============================================================
VALID_TRANSITIONS = {
    "pending": {"in_progress", "failed", "completed"},
    "in_progress": {"passed", "failed", "completed", "pending"},
    "passed": {"completed"},
    "failed": {"in_progress", "pending"},
    "completed": {"in_progress", "passed", "pending"},
}

VALID_STATUSES = set()
for from_s, to_set in VALID_TRANSITIONS.items():
    VALID_STATUSES.add(from_s)
    VALID_STATUSES.update(to_set)


def safe_filename(name):
    """将任务名转换为安全的文件名"""
    if not name or not name.strip():
        return "unnamed-task"
    # 替换文件系统不允许的字符
    invalid_chars = '<>:"/\\|?*'
    safe = name.strip()
    for c in invalid_chars:
        safe = safe.replace(c, "-")
    safe = safe.rstrip(".")
    if not safe.strip():
        return "unnamed-task"
    return safe


def read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        raw = f.read()
    # Python 2 的 json.loads 接受 str，Python 3 接受 bytes
    return json.loads(raw)


def write_json(path, data):
    """写入 JSON 文件，UTF-8 编码"""
    with open(path, "wb") as f:
        content = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
        # Python 2/3 兼容: 将 str 编码为 UTF-8 bytes
        if isinstance(content, str):
            f.write(content.encode("utf-8"))
        else:
            f.write(content)


def append_text(path, line):
    """追加一行文本到文件，UTF-8 编码"""
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, "ab") as f:
        if isinstance(line, str):
            line = line.encode("utf-8")
        f.write(line)
        f.write(b"\n")


def read_utf8_lines(path):
    """逐行读取 UTF-8 文件"""
    lines = []
    if os.path.exists(path):
        with open(path, "rb") as f:
            for raw_line in f:
                lines.append(raw_line.decode("utf-8").rstrip("\r\n"))
    return lines


def get_tasks(data):
    """从 features.json 数据中提取任务列表，支持新旧两种格式"""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "initial_tasks" in data:
            return data["initial_tasks"]
        if "tasks" in data:
            return data["tasks"]
    return []


def get_verify_config(data):
    """获取验证配置"""
    if isinstance(data, dict):
        return data.get("verify_config", {})
    return {}


def zfill_task_id(task_id):
    """将任务 ID 中的数字部分补齐为 3 位"""
    match = re.match(r'^([A-Za-z]*)(\d+)$', task_id)
    if match:
        prefix = match.group(1)
        num = match.group(2)
        return prefix + num.zfill(3)
    return task_id


def find_task(task_id, tasks):
    """按 ID 查找任务"""
    for task in tasks:
        if task.get("id") == task_id or zfill_task_id(str(task.get("id", ""))) == zfill_task_id(task_id):
            return task
    return None


def get_depends_on(task):
    """获取任务的依赖列表"""
    deps = task.get("depends_on", [])
    if isinstance(deps, list):
        return [str(d) for d in deps if d and str(d).strip()]
    return []


def get_task_duration(task):
    """计算任务持续时间（分钟），如果有 created_at 和 updated_at"""
    created = task.get("metadata", {}).get("created_at", "") if isinstance(task.get("metadata"), dict) else ""
    updated = task.get("updated_at", "")
    if created and updated:
        try:
            # 尝试解析 ISO 格式时间戳
            import datetime
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    t1 = datetime.datetime.strptime(created[:19], fmt)
                    t2 = datetime.datetime.strptime(updated[:19], fmt)
                    delta = t2 - t1
                    return int(delta.total_seconds() / 60)
                except ValueError:
                    continue
        except Exception:
            pass
    return None


def is_passed_status(task):
    """检查任务是否已通过"""
    return task.get("status") in ("passed", "completed")


def validate_transition(task_id, current_status, new_status, all_tasks, task_by_id):
    """
    验证状态转换的合法性。
    返回 (是否合法, 错误消息)
    """
    # 检查新状态是否有效
    if new_status not in VALID_STATUSES:
        return False, u"无效状态: {0}".format(new_status)

    # 检查转换是否在允许表中
    allowed = VALID_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        return False, u"非法状态转换: {0} 不能从 {1} 转为 {2}".format(
            task_id, current_status, new_status)

    # P1-3: in_progress 按 parallel_group 检查唯一性
    # 相同 parallel_group 不能并行执行，不同 group 可以并行
    # parallel_group 为空时视为默认组（全部串行）
    if new_status == "in_progress" and current_status != "in_progress":
        target = find_task(task_id, all_tasks)
        target_group = str(target.get("parallel_group", "")) if target else ""
        for t in all_tasks:
            tid = str(t.get("id", ""))
            if tid == task_id:
                continue
            if t.get("status") != "in_progress":
                continue
            other_group = str(t.get("parallel_group", ""))
            # 相同 parallel_group 不能并行，空 group 视为相同（全部串行）
            if target_group == other_group or (not target_group and not other_group):
                return False, u"并行组冲突: 任务 {0} 与 {1} 在同一 parallel_group '{2}' 中，不能同时执行".format(
                    task_id, tid, target_group or u"(默认组)")

    # in_progress: 检查依赖是否已通过
    if new_status == "in_progress" and current_status != "in_progress":
        target = find_task(task_id, all_tasks)
        if target:
            deps = get_depends_on(target)
            missing_deps = [d for d in deps if d not in task_by_id]
            unmet_deps = [d for d in deps if d in task_by_id and not is_passed_status(task_by_id[d])]
            if missing_deps:
                return False, u"依赖任务不存在: {0}".format(", ".join(missing_deps))
            if unmet_deps:
                return False, u"依赖任务未完成: {0}".format(", ".join(unmet_deps))

    return True, ""


def append_history(features_root, task_id, from_status, to_status, message):
    """追加状态转换历史到 harness-history.jsonl"""
    history_path = os.path.join(features_root, "harness-history.jsonl")
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task_id": task_id,
        "from": from_status,
        "to": to_status,
        "message": message or ""
    }
    append_text(history_path, json.dumps(record, ensure_ascii=False))


def check_stall(history_path, task_id):
    """检查同一任务是否连续失败 3 次以上"""
    if not os.path.exists(history_path):
        return False
    lines = read_utf8_lines(history_path)
    fail_count = 0
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("task_id") == task_id and record.get("to") == "failed":
            fail_count += 1
        elif record.get("task_id") != task_id and record.get("to") == "failed":
            # 其他任务失败不算
            pass
        else:
            # 遇到此任务非失败状态转换则重置计数
            if record.get("task_id") == task_id:
                break
    return fail_count >= 3


def write_report(reports_dir, task, project_root, progress_path, current_status, new_status, log_message):
    """生成任务报告 Markdown 文件"""
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    task_id = str(task.get("id", ""))
    task_name = str(task.get("name", ""))
    safe_name = safe_filename(task_name)
    report_path = os.path.join(reports_dir, "{0}-{1}.md".format(task_id, safe_name))

    deps = get_depends_on(task)
    deps_text = ", ".join(deps) if deps else u"无"
    priority = task.get("priority", 0)
    test_command = str(task.get("test_command", "")) or u"(无)"
    last_error = str(task.get("last_error", "")) or u"无"
    updated_at = str(task.get("updated_at", ""))

    # 验收标准
    criteria = task.get("acceptance_criteria", [])
    if criteria and isinstance(criteria, list):
        criteria_list = ["- {0}".format(c) for c in criteria if c and str(c).strip()]
    else:
        criteria_list = ["- (无)"]
    criteria_section = "\n".join(criteria_list)

    # 历史记录
    history_lines = []
    if os.path.exists(progress_path):
        task_pattern = re.escape(task_id)
        with open(progress_path, "rb") as f:
            for raw_line in f:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if re.search(r'\|\s*' + task_pattern + r'\s*\|', line):
                    history_lines.append("- " + line)
    if not history_lines:
        history_lines.append("- (无历史记录)")
    history_section = "\n".join(history_lines)

    # 状态摘要
    status_summary = {
        "passed": u"通过",
        "failed": u"失败",
        "in_progress": u"进行中",
        "completed": u"完成",
        "pending": u"待处理"
    }.get(new_status, u"未知")

    display_message = log_message if log_message else u"(无具体信息)"

    report_content = u"""# {0} - {1}

## 基本信息
- 任务 ID: `{0}`
- 任务名称: {1}
- 当前状态: `{2}`
- 依赖任务: `{3}`
- 优先级: `{4}`
- 测试命令: `{5}`

### 验收标准
{6}

## 状态变更
- 最新更新时间(UTC): `{7}`
- 状态变更: `{8} -> {9}`
- 变更结果: {10}
- 说明: {11}
- 错误信息: {12}

## claude-progress.txt 历史
{13}
""".format(
        task_id, task_name, new_status, deps_text, priority, test_command,
        criteria_section, updated_at, current_status, new_status,
        status_summary, display_message, last_error, history_section
    )

    with open(report_path, "wb") as f:
        f.write(report_content.encode("utf-8"))

    return report_path


def main():
    parser = argparse.ArgumentParser(description=u"更新任务进度状态")
    parser.add_argument("--task-id", required=True, help=u"任务 ID")
    parser.add_argument("--status", required=True, choices=sorted(VALID_STATUSES), help=u"新状态")
    parser.add_argument("--message", default="", help=u"日志消息")
    parser.add_argument("--project-root", default=".", help=u"项目根目录")

    args = parser.parse_args()
    task_id = args.task_id
    new_status = args.status
    log_message = args.message
    project_root = os.path.abspath(args.project_root)

    # ============================================================
    # 路径定义
    # ============================================================
    claude_root = os.path.join(project_root, ".claude")
    features_root = os.path.join(claude_root, "state")
    # P1-5: 优先使用 features.active.json，向后兼容 features.json
    active_path = os.path.join(features_root, "features.active.json")
    legacy_path = os.path.join(features_root, "features.json")
    features_path = active_path if os.path.exists(active_path) else legacy_path
    archive_path = os.path.join(features_root, "features.archive.json")
    progress_path = os.path.join(features_root, "claude-progress.txt")
    history_path = os.path.join(features_root, "harness-history.jsonl")
    reports_dir = os.path.join(project_root, "docs", "reports")

    # ============================================================
    # 检查状态文件是否存在
    # ============================================================
    if not os.path.exists(features_path):
        print(u"错误: 未找到状态文件: {0}".format(features_path))
        sys.exit(0)

    # ============================================================
    # 读取和解析 active 状态文件
    # ============================================================
    try:
        data = read_json(features_path)
    except Exception as e:
        print(u"错误: 解析 {0} 失败: {1}".format(os.path.basename(features_path), e))
        sys.exit(0)

    tasks = get_tasks(data)
    if not tasks:
        print(u"错误: features.json 中未找到任务列表")
        sys.exit(0)

    # 建立 ID -> task 的映射
    task_by_id = {}
    for t in tasks:
        tid = str(t.get("id", ""))
        if tid:
            task_by_id[tid] = t

    # ============================================================
    # 查找目标任务
    # ============================================================
    target = find_task(task_id, tasks)
    if not target:
        print(u"错误: 未找到任务 {0}".format(task_id))
        sys.exit(0)

    current_status = str(target.get("status", ""))

    # ============================================================
    # 验证状态转换
    # ============================================================
    valid, error_msg = validate_transition(task_id, current_status, new_status, tasks, task_by_id)
    if not valid:
        print(u"错误: {0}".format(error_msg))
        sys.exit(0)

    # ============================================================
    # Oracle 验证门: 仅在转为 passed 时执行
    # ============================================================
    verify_config = get_verify_config(data)
    verify_enabled = verify_config.get("verify_enabled", False) is True
    verify_command = str(verify_config.get("verify_command", "") or "")

    if new_status == "passed" and verify_enabled and verify_command.strip():
        print(u"[Oracle 验证门] 开始执行验证命令...")
        print(u"[验证命令] {0}".format(verify_command))
        verify_timeout = int(verify_config.get("verify_timeout_seconds", 120))

        try:
            proc = subprocess.Popen(
                verify_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root
            )
            stdout_data, stderr_data = proc.communicate(timeout=verify_timeout)
            exit_code = proc.returncode

            # 解码输出
            stdout_text = stdout_data.decode("utf-8", errors="replace") if stdout_data else ""
            stderr_text = stderr_data.decode("utf-8", errors="replace") if stderr_data else ""

            verify_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            verify_log = [
                u"--- Oracle 验证门 ---",
                u"时间: {0}".format(verify_timestamp),
                u"任务: {0} -> passed".format(task_id),
                u"验证命令: {0}".format(verify_command),
                u"退出码: {0}".format(exit_code),
            ]
            if stdout_text.strip():
                verify_log.append(u"标准输出:")
                verify_log.append(stdout_text.strip())
            if stderr_text.strip():
                verify_log.append(u"错误输出:")
                verify_log.append(stderr_text.strip())

            verify_log_text = "\n".join(verify_log)
            append_text(progress_path, verify_log_text)

            if exit_code != 0:
                print(u"[Oracle 验证门] 验证失败 (exit code: {0})，转为 failed".format(exit_code))
                new_status = "failed"
                failure_detail = u"Oracle 验证门失败: 验证命令返回退出码 {0}".format(exit_code)
                if stderr_text.strip():
                    failure_detail += "\n" + stderr_text.strip()
                log_message = failure_detail
            else:
                print(u"[Oracle 验证门] 验证通过")

        except subprocess.TimeoutExpired:
            proc.kill()
            print(u"[Oracle 验证门] 验证超时 ({0}s)，转为 failed".format(verify_timeout))
            new_status = "failed"
            log_message = u"Oracle 验证门超时 ({0}s)".format(verify_timeout)
        except Exception as e:
            print(u"[Oracle 验证门] 验证执行异常: {0}，转为 failed".format(e))
            new_status = "failed"
            log_message = u"Oracle 验证门执行异常: {0}".format(e)

    # ============================================================
    # 更新任务状态
    # ============================================================
    target["status"] = new_status
    target["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if new_status == "failed":
        target["last_error"] = log_message
    else:
        target["last_error"] = ""

    # ============================================================
    # 写回 active 状态文件
    # ============================================================
    try:
        write_json(features_path, data)
    except Exception as e:
        print(u"错误: 写入 {0} 失败: {1}".format(os.path.basename(features_path), e))
        sys.exit(0)

    # ============================================================
    # P1-5: 归档处理 —— 使用 active/archive 拆分时，passed/failed 移入归档
    # ============================================================
    if os.path.exists(active_path) and new_status in ("passed", "failed", "completed"):
        try:
            # 读取或创建归档文件
            if os.path.exists(archive_path):
                archive_data = read_json(archive_path)
            else:
                archive_data = {"tasks": []}
            # 确保归档文件包含 verify_config
            archive_data["verify_config"] = data.get("verify_config", {
                "verify_enabled": False,
                "verify_command": "",
                "verify_timeout_seconds": 120
            })
            # 从 active 中移除该任务
            active_tasks = get_tasks(data)
            data["tasks"] = [t for t in active_tasks if str(t.get("id", "")) != task_id]
            # 添加到归档（避免重复）
            archive_tasks = get_tasks(archive_data)
            if not find_task(task_id, archive_tasks):
                archive_tasks.append(dict(target))  # 深拷贝任务数据
                archive_data["tasks"] = archive_tasks
            # 同时写回两个文件
            write_json(features_path, data)
            write_json(archive_path, archive_data)
            print(u"[归档] 任务 {0} 已移至 features.archive.json".format(task_id))
        except Exception as e:
            print(u"警告: 归档任务 {0} 失败: {1}".format(task_id, e))

    # ============================================================
    # 追加日志到 claude-progress.txt
    # ============================================================
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    progress_line = "{0} | {1} | {2} -> {3} | {4}".format(
        timestamp, task_id, current_status, new_status, log_message)
    append_text(progress_path, progress_line)

    # ============================================================
    # P1-1: 追加状态转换历史到 harness-history.jsonl
    # ============================================================
    append_history(features_root, task_id, current_status, new_status, log_message)

    # ============================================================
    # P1-1: Stall 检测 —— 同一任务连续失败 3+ 次
    # ============================================================
    if new_status == "failed":
        if check_stall(history_path, task_id):
            print(u"WARNING: 任务 {0} 已连续失败 3 次以上，请检查是否存在根本性问题".format(task_id))

    # ============================================================
    # passed/completed 时生成报告
    # ============================================================
    report_path = ""
    if new_status in ("passed", "completed"):
        report_path = write_report(
            reports_dir, target, project_root, progress_path,
            current_status, new_status, log_message
        )

    # ============================================================
    # 输出结果
    # ============================================================
    print(u"完成: {0} 状态从 {1} 变为 {2}".format(task_id, current_status, new_status))
    if report_path:
        print(u"报告已生成: {0}".format(report_path))

    sys.exit(0)


if __name__ == "__main__":
    main()
