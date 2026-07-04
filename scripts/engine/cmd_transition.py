#!/usr/bin/env python
# -*- coding: utf-8 -*-
# cmd_transition.py — 状态机状态流转
# 读取 .claude/animus/features.json，校验并执行任务状态转换
# 兼容 Python 2.7+ 和 3.x

from __future__ import print_function, unicode_literals
import json
import os
import subprocess
import sys
import time


# ============================================================
# 常量
# ============================================================

# 合法状态转换表: from_state -> {允许的 to_state 集合}
VALID_TRANSITIONS = {
    "pending": {"in_progress", "failed", "completed"},
    "in_progress": {"passed", "failed", "completed", "pending"},
    "passed": {"completed"},
    "failed": {"in_progress", "pending"},
    "completed": {"in_progress", "passed", "pending"},
}

# 所有合法状态集合
VALID_STATUSES = set()
for from_s, to_set in VALID_TRANSITIONS.items():
    VALID_STATUSES.add(from_s)
    VALID_STATUSES.update(to_set)

FEATURES_REL_PATH = os.path.join(".claude", "animus", "features.json")


# ============================================================
# 兼容层
# ============================================================

def _text(value):
    """将值强制转为 str（Python 2 下为字节串，Python 3 下为文本）。"""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _ensure_str(obj):
    """确保字符串类型在 Python 2/3 下正确比较。"""
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    return obj


def _read_json(path):
    """读取 JSON 文件，兼容 Python 2/3。"""
    with open(path, "rb") as f:
        raw = f.read()
    return json.loads(raw)


def _write_json(path, data):
    """写入 JSON 文件，UTF-8 编码，兼容 Python 2/3。"""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    with open(path, "wb") as f:
        if isinstance(content, str):
            f.write(content.encode("utf-8"))
        else:
            f.write(content)
        f.write(b"\n")


def _now_iso():
    """返回当前时间的 ISO 8601 格式字符串。"""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _find_features_json():
    """按优先级搜索 features.json 文件路径。"""
    # 1) 环境变量显式指定
    env_path = os.environ.get("ANIMUS_FEATURES_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2) 从当前目录向上查找
    cwd = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(cwd, FEATURES_REL_PATH)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cwd)
        if parent == cwd:
            break
        cwd = parent

    # 3) 从脚本所在目录向上查找
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for parent in (script_dir, os.path.join(script_dir, "..", ".."),
                   os.path.join(script_dir, "..", "..", "..")):
        candidate = os.path.join(parent, FEATURES_REL_PATH)
        if os.path.isfile(candidate):
            return candidate

    return None


def _get_tasks(data):
    """从 features.json 数据中提取任务列表，支持多种格式。"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("initial_tasks", "tasks", "features"):
            if key in data:
                val = data[key]
                # 如果是 dict 格式 {task_id: task_data}，转换为 list
                if isinstance(val, dict):
                    result = []
                    for tid, tdata in val.items():
                        item = {"id": tid}
                        item.update(tdata)
                        result.append(item)
                    return result
                return val
        # 如果只有一个顶层任务对象（如 {"id":"T001",...}），包装成列表
        if "id" in data:
            return [data]
    return []


def _find_task_by_id(task_id, tasks):
    """按 ID 查找任务，支持补齐前导零。"""
    import re

    def zfill_id(tid):
        match = re.match(r'^([A-Za-z]*)(\d+)$', _text(tid))
        if match:
            return match.group(1) + match.group(2).zfill(3)
        return _text(tid)

    target = zfill_id(task_id)
    for task in tasks:
        if zfill_id(task.get("id", "")) == target:
            return task
    return None


def _get_verify_config(data, features_dir):
    """获取验证配置。优先从 config.toml 读取，降级到旧 project-config.json。"""
    # 优先：从 config.toml 读取 project.verify
    try:
        from scripts.config_loader import load_config, get_config_value
        cfg = load_config()
        vc = get_config_value(cfg, "project.verify", {})
        if vc and vc.get("command"):
            return vc
    except Exception:
        pass
    # 降级：从旧的 project-config.json 读取（迁移期兼容）
    config_path = os.path.join(features_dir, "project-config.json")
    if os.path.isfile(config_path):
        try:
            with open(config_path, "rb") as f:
                proj_data = json.loads(f.read())
            if isinstance(proj_data, dict):
                vc = proj_data.get("verify_config")
                if vc:
                    return vc
        except Exception:
            pass
    # 二次降级：从 features.json 读取（向后兼容）
    if isinstance(data, dict):
        vc = data.get("verify_config")
        if vc:
            return vc
    return {}


def _exec_verify_command(verify_command, timeout_seconds=120, cwd=None):
    """
    执行验证命令。
    返回 (success, stdout, stderr)。
    """
    try:
        proc = subprocess.Popen(
            verify_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )
        stdout_data, stderr_data = proc.communicate(timeout=timeout_seconds)
        stdout_text = _text(stdout_data)
        stderr_text = _text(stderr_data)
        return_code = proc.returncode
        success = (return_code == 0)
        return success, stdout_text, stderr_text
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, "", "验证命令超时（{0} 秒）".format(timeout_seconds)
    except Exception as e:
        return False, "", _text(e)


# ============================================================
# 核心函数
# ============================================================

def run(task_id, to, evidence=""):
    """
    执行任务状态转换。

    参数：
        task_id  : str  — 任务 ID（如 "T001"）
        to       : str  — 目标状态
        evidence : str  — 转换的证据/备注（可选）

    返回：
        dict — {
            "success": bool,
            "message": str,
            "task_id": str,
            "from": str or None,
            "to": str,
        }
    """
    # ----------------------------------------------------------
    # 标准化目标状态
    # ----------------------------------------------------------
    to = _ensure_str(to).strip().lower()
    task_id = _ensure_str(task_id).strip()

    # ----------------------------------------------------------
    # 定位 features.json
    # ----------------------------------------------------------
    features_path = _find_features_json()
    if not features_path:
        return {
            "success": False,
            "message": "未找到 features.json（查找路径：.claude/animus/features.json）",
            "task_id": task_id,
            "from": None,
            "to": to,
        }

    features_dir = os.path.dirname(features_path)

    # ----------------------------------------------------------
    # 读取 JSON
    # ----------------------------------------------------------
    try:
        data = _read_json(features_path)
    except (ValueError, IOError) as e:
        return {
            "success": False,
            "message": "读取 features.json 失败: {0}".format(_text(e)),
            "task_id": task_id,
            "from": None,
            "to": to,
        }

    tasks = _get_tasks(data)
    if not tasks:
        return {
            "success": False,
            "message": "features.json 中无任务数据",
            "task_id": task_id,
            "from": None,
            "to": to,
        }

    # ----------------------------------------------------------
    # 查找任务
    # ----------------------------------------------------------
    task = _find_task_by_id(task_id, tasks)
    if task is None:
        return {
            "success": False,
            "message": "未找到任务: {0}".format(task_id),
            "task_id": task_id,
            "from": None,
            "to": to,
        }

    current_status = _ensure_str(task.get("status", "pending")).strip().lower()

    # ----------------------------------------------------------
    # 校验目标状态合法性
    # ----------------------------------------------------------
    if to not in VALID_STATUSES:
        return {
            "success": False,
            "message": "无效的目标状态 '{0}'，允许值: {1}".format(
                to, ", ".join(sorted(VALID_STATUSES))),
            "task_id": task_id,
            "from": current_status,
            "to": to,
        }

    # ----------------------------------------------------------
    # 校验状态转换合法性
    # ----------------------------------------------------------
    allowed = VALID_TRANSITIONS.get(current_status, set())
    if to not in allowed:
        return {
            "success": False,
            "message": "非法状态转换: 任务 {0} 当前状态为 '{1}'，不能转为 '{2}'".format(
                task_id, current_status, to),
            "task_id": task_id,
            "from": current_status,
            "to": to,
        }

    # ----------------------------------------------------------
    # 检查是否已经是目标状态（无操作）
    # ----------------------------------------------------------
    if current_status == to:
        return {
            "success": True,
            "message": "任务 {0} 已经是 '{1}' 状态，无需转换".format(task_id, to),
            "task_id": task_id,
            "from": current_status,
            "to": to,
        }

    # ----------------------------------------------------------
    # 约束：同一时间只能有一个 in_progress 任务
    # ----------------------------------------------------------
    if to == "in_progress" and current_status != "in_progress":
        for t in tasks:
            tid = _text(t.get("id", ""))
            if tid == task_id:
                continue
            if _ensure_str(t.get("status", "")).strip().lower() == "in_progress":
                return {
                    "success": False,
                    "message": "冲突: 任务 {0} 已在 in_progress 状态，无法同时执行多个任务".format(tid),
                    "task_id": task_id,
                    "from": current_status,
                    "to": to,
                }

    # ----------------------------------------------------------
    # 如果 to=passed，检查并执行验证命令
    # ----------------------------------------------------------
    verify_log = []
    if to == "passed":
        verify_config = _get_verify_config(data, features_dir)

        # 优先检查任务级 verify_command
        verify_command = _text(task.get("verify_command", "") or "").strip()

        # 如果没有任务级 verify_command，检查全局配置
        if not verify_command:
            verify_enabled = verify_config.get("verify_enabled", False)
            if verify_enabled in (True, "true", "True", 1, "1"):
                verify_command = _text(verify_config.get("verify_command", "") or "").strip()

        if verify_command:
            verify_timeout = int(verify_config.get("verify_timeout_seconds", 120)) if verify_config else 120
            verify_log.append("执行验证命令: {0}".format(verify_command))

            success, stdout_text, stderr_text = _exec_verify_command(
                verify_command,
                timeout_seconds=verify_timeout,
                cwd=features_dir if features_dir else None,
            )

            if stdout_text:
                verify_log.append("标准输出:")
                verify_log.append(stdout_text.strip())
            if stderr_text:
                verify_log.append("错误输出:")
                verify_log.append(stderr_text.strip())

            if not success:
                # 验证失败：记录错误并返回
                error_msg = "验证命令执行失败（返回码非零）"
                if stderr_text:
                    error_msg = stderr_text.strip().split("\n")[-1]
                elif stdout_text:
                    error_msg = stdout_text.strip().split("\n")[-1]
                verify_log.append("结果: 失败 - {0}".format(error_msg))

                task["status"] = current_status  # 保持原状态
                task["last_error"] = error_msg
                task["updated_at"] = _now_iso()
                task["verify_log"] = verify_log

                _write_json(features_path, data)

                return {
                    "success": False,
                    "message": "验证命令未通过: {0}".format(error_msg),
                    "task_id": task_id,
                    "from": current_status,
                    "to": to,
                    "verify_log": verify_log,
                }

            verify_log.append("结果: 通过")
        else:
            verify_log.append("无验证命令，跳过验证")

    # ----------------------------------------------------------
    # 执行状态转换
    # ----------------------------------------------------------
    from_status = current_status

    # 更新任务状态
    task["status"] = to
    task["updated_at"] = _now_iso()

    # 清除 last_error 当转换到非失败状态
    if to != "failed":
        task["last_error"] = ""

    # 记录验证日志（如果有）
    if verify_log:
        task["verify_log"] = verify_log

    # 记录 evidence
    if evidence:
        task["last_evidence"] = _text(evidence)

    # ----------------------------------------------------------
    # 写入 features.json
    # ----------------------------------------------------------
    try:
        _write_json(features_path, data)
    except IOError as e:
        return {
            "success": False,
            "message": "写入 features.json 失败: {0}".format(_text(e)),
            "task_id": task_id,
            "from": from_status,
            "to": to,
        }

    return {
        "success": True,
        "message": "任务 {0} 状态从 '{1}' 转换为 '{2}'".format(task_id, from_status, to),
        "task_id": task_id,
        "from": from_status,
        "to": to,
        "verify_log": verify_log if verify_log else None,
    }


# ============================================================
# 命令行入口
# ============================================================

def main():
    """
    命令行调用入口。
    用法: python cmd_transition.py <task_id> <to> [evidence]
    """
    if len(sys.argv) < 3:
        print("用法: python cmd_transition.py <task_id> <to> [evidence]", file=sys.stderr)
        print("示例: python cmd_transition.py T001 in_progress", file=sys.stderr)
        sys.exit(1)

    task_id = sys.argv[1]
    to = sys.argv[2]
    evidence = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""

    result = run(task_id, to, evidence)

    # 输出结果
    if result.get("verify_log"):
        for line in result["verify_log"]:
            print(line)

    if result["success"]:
        print(result["message"])
        sys.exit(0)
    else:
        print("ERROR: {0}".format(result["message"]), file=sys.stderr)
        sys.exit(1)


# ============================================================
# 模块导出
# ============================================================

__all__ = ["run", "VALID_TRANSITIONS", "VALID_STATUSES"]


if __name__ == "__main__":
    main()
