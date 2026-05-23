#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def get_priority(task: dict) -> int:
    value = task.get("priority", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_depends_on(task: dict) -> list[str]:
    depends_on = task.get("depends_on", [])
    if isinstance(depends_on, list):
        return [str(item) for item in depends_on if str(item).strip()]
    return []


def can_run(task: dict, status_by_id: dict[str, str]) -> bool:
    for dep_id in get_depends_on(task):
        if status_by_id.get(dep_id) != "passed":
            return False
    return True


def main() -> int:
    if len(sys.argv) > 1:
        harness_root = Path(sys.argv[1])
    else:
        # Prefer repo-root invocation: python .claude/harness/show-status.py
        default_root = Path(".claude/harness")
        if default_root.exists():
            harness_root = default_root
        else:
            harness_root = Path(__file__).resolve().parent

    features_path = harness_root / "features.json"

    if not features_path.exists():
        print(f"未找到 features.json: {features_path}")
        return 1

    tasks = json.loads(features_path.read_text(encoding="utf-8"))
    status_by_id = {str(task.get("id", "")): str(task.get("status", "")) for task in tasks}

    total = len(tasks)
    passed = sum(1 for task in tasks if task.get("status") == "passed")
    failed_tasks = [task for task in tasks if task.get("status") == "failed"]
    in_progress = next((task for task in tasks if task.get("status") == "in_progress"), None)
    pending_tasks = [task for task in tasks if task.get("status") == "pending"]

    executable_pending = [task for task in pending_tasks if can_run(task, status_by_id)]
    executable_pending.sort(key=lambda task: (-get_priority(task), str(task.get("id", ""))))
    next_pending = executable_pending[0] if executable_pending else None

    print(f"任务总数: {total}")
    print(f"已通过: {passed}")
    print(f"失败: {len(failed_tasks)}")

    if in_progress:
        task_id = in_progress.get("id", "UNKNOWN")
        task_name = in_progress.get("name", "")
        updated_at = in_progress.get("updated_at", "")
        print(f"进行中: {task_id} {task_name}")
        if updated_at:
            print(f"进行中更新时间: {updated_at}")
    elif next_pending:
        task_id = next_pending.get("id", "UNKNOWN")
        task_name = next_pending.get("name", "")
        priority = get_priority(next_pending)
        print(f"下一个可执行任务: {task_id} {task_name} (priority={priority})")

        blocked = len(pending_tasks) - len(executable_pending)
        if blocked > 0:
            print(f"被依赖阻塞的 pending 任务: {blocked}")
    else:
        print("所有任务均已完成。")

    if failed_tasks:
        failed_tasks.sort(key=lambda task: (-get_priority(task), str(task.get("id", ""))))
        top_failed = failed_tasks[0]
        err = str(top_failed.get("last_error", "")).strip()
        task_id = top_failed.get("id", "UNKNOWN")
        task_name = top_failed.get("name", "")
        print(f"待处理失败任务: {task_id} {task_name}")
        if err:
            print(f"最近失败原因: {err}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
