#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容

from __future__ import print_function
import json
import os
import sys


# ponytail: sys.stdout.reconfigure + bare print handles GBK, no wrapper needed
if sys.version_info[0] >= 3 and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
u_print = print  # ponytail: print() is fine after reconfigure


# ponytail: _c() inlined below, only caller was render_summary count_parts


# ---------------------------------------------------------------------------
# 以下为原有函数（保持签名不变）
# ---------------------------------------------------------------------------

def get_priority(task):
    value = task.get("priority", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_depends_on(task):
    depends_on = task.get("depends_on", [])
    if isinstance(depends_on, list):
        return [str(item) for item in depends_on if str(item).strip()]
    return []


def can_run(task, status_by_id):
    """判断任务依赖是否已满足。

    状态机契约：依赖任务状态为 passed 或 completed 时，依赖视为满足。
    与 PowerShell 版 pre-compact.ps1:43 和 pre-compact.sh:30 保持一致。
    """
    for dep_id in get_depends_on(task):
        if status_by_id.get(dep_id) not in ("passed", "completed"):
            return False
    return True


def read_json(path):
    """读取 JSON 文件，兼容 Python 2/3 以及 UTF-8 BOM。"""
    with open(path, "rb") as f:
        raw = f.read()
    # 处理可能存在的 UTF-8 BOM（PowerShell 5.1 的 -Encoding UTF8 会添加 BOM）
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    return json.loads(raw)


def get_tasks(data):
    """从 features.json 中提取任务列表，支持新旧两种格式"""
    if isinstance(data, list):
        # 旧格式：直接是任务数组
        return data
    elif isinstance(data, dict):
        # 新格式：有 initial_tasks 字段
        if "initial_tasks" in data:
            return data["initial_tasks"]
        # 也支持 tasks 字段
        if "tasks" in data:
            return data["tasks"]
    return []


# ---------------------------------------------------------------------------
# 新增功能 2：build_tree - 构建依赖树
# ---------------------------------------------------------------------------

def build_tree(tasks, status_by_id):
    """返回 list of dicts，每个节点有 id、children（同样结构的 list）。

    关键规则：每个任务在树中只出现一次。
    算法：
    1. 建立反向索引（子→父映射）
    2. 找出根任务（depends_on 为空）
    3. 从根任务开始 DFS 遍历，用 visited set 记录
    4. 多父节点任务只在首次出现位置展示，其余标注 [亦依赖 XXX]
    5. children 按 priority 降序、ID 升序排列
    """
    # task_id -> task dict
    task_map = {str(t.get("id", "")): t for t in tasks}
    existing_ids = set(task_map.keys())

    # 找出每个任务的直接子任务：父 -> [子IDs]
    dag_children = {}
    for t in tasks:
        tid = str(t.get("id", ""))
        if not tid or tid not in existing_ids:
            continue
        deps = get_depends_on(t)
        # 对于每个依赖（父），将当前任务添加为子
        for dep_id in deps:
            if dep_id not in existing_ids:
                continue
            if dep_id not in dag_children:
                dag_children[dep_id] = []
            dag_children[dep_id].append(tid)

    # 找出根任务（无依赖或依赖都不在任务集中）
    root_ids = []
    for t in tasks:
        tid = str(t.get("id", ""))
        if not tid or tid not in existing_ids:
            continue
        deps = get_depends_on(t)
        real_deps = [d for d in deps if d in existing_ids]
        if not real_deps:
            root_ids.append(tid)

    # 排序：priority 降序，ID 升序
    def sort_key(tid):
        t = task_map.get(tid, {})
        return (-get_priority(t), tid)

    root_ids.sort(key=sort_key)

    # 收集多父节点信息：child_id -> [parent_ids]
    child_to_parents = {}
    for t in tasks:
        tid = str(t.get("id", ""))
        if not tid or tid not in existing_ids:
            continue
        deps = get_depends_on(t)
        for dep_id in deps:
            if dep_id not in existing_ids:
                continue
            if tid not in child_to_parents:
                child_to_parents[tid] = []
            child_to_parents[tid].append(dep_id)

    # DFS 构建树（每个节点只出现一次）
    visited = set()

    def build_node(tid):
        """递归构建单节点。"""
        if tid in visited:
            return None
        visited.add(tid)
        node = {"id": tid, "children": []}
        # 获取 dag_children 中的子任务
        children_ids = dag_children.get(tid, [])
        # 过滤已在访问中的
        children_ids = [c for c in children_ids if c not in visited]
        children_ids.sort(key=sort_key)
        for cid in children_ids:
            child_node = build_node(cid)
            if child_node is not None:
                node["children"].append(child_node)
        return node

    # 从根节点开始构建
    tree = []
    for rid in root_ids:
        node = build_node(rid)
        if node is not None:
            tree.append(node)

    # 处理孤岛：未出现在树中的任务（既无依赖也无子任务，或依赖链断裂）
    all_treed = set()

    def collect_ids(nodes):
        ids = set()
        for n in nodes:
            ids.add(n["id"])
            ids |= collect_ids(n.get("children", []))
        return ids

    all_treed = collect_ids(tree)

    for t in tasks:
        tid = str(t.get("id", ""))
        if tid and tid not in all_treed and tid in existing_ids:
            node = {"id": tid, "children": []}
            tree.append(node)
            all_treed.add(tid)

    # 将多父节点信息附着到节点上（供 render_tree 使用）
    # 通过函数属性传递
    build_tree._multi_parent_map = child_to_parents

    return tree


# ---------------------------------------------------------------------------
# 新增功能 6：compute_block_chains - 阻塞链分析
# ---------------------------------------------------------------------------

def compute_block_chains(tasks, status_by_id):
    """从每个 pending 任务向上回溯依赖链，找出最深的前 5 条。

    返回: list of dicts, 每个有 task_id、chain（ancestor ids 列表）、depth
    """
    task_map = {str(t.get("id", "")): t for t in tasks}
    chains = []

    for t in tasks:
        tid = str(t.get("id", ""))
        if not tid:
            continue
        if t.get("status") != "pending":
            continue
        deps = get_depends_on(t)
        # 找到未满足的依赖
        blocked_by = [d for d in deps if status_by_id.get(d) not in ("passed", "completed")]
        if not blocked_by:
            continue

        # 对每个未满足依赖回溯其依赖链
        for dep_id in blocked_by:
            chain = [dep_id]
            # 向上回溯
            current = dep_id
            visited_in_chain = set([tid, current])
            while current:
                dep_task = task_map.get(current)
                if dep_task is None:
                    break
                grand_deps = get_depends_on(dep_task)
                # 找第一个未满足的祖父依赖（且不在已访问链中）
                next_dep = None
                for gd in grand_deps:
                    if status_by_id.get(gd) not in ("passed", "completed") and gd not in visited_in_chain:
                        next_dep = gd
                        break
                if next_dep is None:
                    break
                visited_in_chain.add(next_dep)
                chain.append(next_dep)
                current = next_dep

            chains.append({
                "task_id": tid,
                "chain": chain,
                "depth": len(chain),
            })

    # 按深度降序，取前 5
    chains.sort(key=lambda x: -x["depth"])
    return chains[:5]


# ---------------------------------------------------------------------------
# 新增功能 3：render_summary - box-drawing 看板
# ---------------------------------------------------------------------------

def render_summary(tasks, total, passed, failed, in_progress, pending):
    """输出 box-drawing 看板摘要。"""
    # 尝试读取 iteration_name
    iteration_name = u"animus"
    state_root_global = getattr(render_summary, "_state_root", None)
    if state_root_global:
        config_path = os.path.join(state_root_global, "project-config.json")
        if os.path.exists(config_path):
            try:
                config_data = read_json(config_path)
                if isinstance(config_data, dict):
                    iteration_name = config_data.get("iteration_name", iteration_name)
            except Exception:
                pass

    # 进度
    progress_pct = int(float(passed) / total * 100) if total > 0 else 0
    bar_filled = int(progress_pct / 100.0 * 16)
    bar_empty = 16 - bar_filled
    bar = u"█" * bar_filled + u"░" * bar_empty

    # 整体状态 emoji
    if total > 0 and passed == total:
        overall = u"\U0001F7E2"  # 🟢
    elif failed > 0:
        overall = u"\U0001F534"  # 🔴
    elif in_progress is not None:
        overall = u"\U0001F7E1"  # 🟡
    elif pending == total:
        overall = u"⚪"      # ⚪
    else:
        overall = u"\U0001F7E1"  # 🟡

    # 构建 box
    width = 38
    title = u"{0} animus 迭代{1}".format(overall, u" - " + iteration_name if iteration_name != "animus" else u"")
    bar_line = u"进度: {0}  {1}% ({2}/{3})".format(bar, progress_pct, passed, total)

    # 计数行（ansi color inline，ponytail: no separate _c() helper）
    _is_tty = sys.stdout.isatty()
    _gr = u"\033[92m" if _is_tty else u""; _re = u"\033[91m" if _is_tty else u""; _ye = u"\033[93m" if _is_tty else u""; _rst = u"\033[0m" if _is_tty else u""
    count_parts = []
    count_parts.append(u"{0}✅ {1}{2}".format(_gr, passed, _rst))
    count_parts.append(u"{0}❌ {1}{2}".format(_re, failed, _rst) if failed > 0 else u"❌ 0")
    count_parts.append(u"{0}\U0001F7E1 {1}{2}".format(_ye, 1 if in_progress else 0, _rst))
    count_parts.append(u"⏳ {0}".format(pending))

    # 计算可见长度（去掉 ANSI 转义后的实际长度）
    import re
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

    def visible_len(s):
        return len(ansi_escape.sub('', s))

    count_line = u"  ".join(count_parts)

    # Oracle 验证门配置
    verify_line = None
    state_root = getattr(render_summary, "_state_root", None)
    if state_root:
        verify_config = None
        config_path = os.path.join(state_root, "project-config.json")
        if os.path.exists(config_path):
            try:
                config_data = read_json(config_path)
                verify_config = config_data.get("verify_config") if isinstance(config_data, dict) else None
            except Exception:
                verify_config = None
        if verify_config:
            enabled = verify_config.get("verify_enabled", False)
            cmd = verify_config.get("verify_command", "")
            status_text = u"已启用" if enabled else u"未启用"
            cmd_text = cmd if cmd else u"(无)"
            verify_line = u"Oracle 验证门: {0} | 命令: {1}".format(status_text, cmd_text)

    lines = []
    lines.append(u"╔" + u"═" * width + u"╗")  # ╔═╗
    # 标题行
    title_visible = u"  {0}".format(title)
    title_pad = width - visible_len(title_visible) + 1
    if title_pad < 0:
        title_pad = 0
    lines.append(u"║{0}{1}║".format(title_visible, u" " * title_pad))  # ║ ║
    # 分隔线
    lines.append(u"║  " + u"─" * (width - 2) + u"  ║")  # ║──║
    # 进度条
    bar_visible = u"  {0}".format(bar_line)
    bar_pad = width - visible_len(bar_visible) + 1
    if bar_pad < 0:
        bar_pad = 0
    lines.append(u"║{0}{1}║".format(bar_visible, u" " * bar_pad))
    # 计数行
    count_visible = u"  {0}".format(count_line)
    count_pad = width - visible_len(count_visible) + 1
    if count_pad < 0:
        count_pad = 0
    lines.append(u"║{0}{1}║".format(count_visible, u" " * count_pad))
    # Oracle 验证门
    if verify_line:
        v_visible = u"  {0}".format(verify_line)
        v_pad = width - visible_len(v_visible) + 1
        if v_pad < 0:
            v_pad = 0
        lines.append(u"║{0}{1}║".format(v_visible, u" " * v_pad))
    # 底框
    lines.append(u"╚" + u"═" * width + u"╝")  # ╚═╝

    u_print(u"")
    for line in lines:
        u_print(line)
    u_print(u"")


# ---------------------------------------------------------------------------
# 新增功能 4：render_tree - ASCII 树渲染（递归）
# ---------------------------------------------------------------------------

def render_tree(tree_nodes, status_by_id, task_map, indent=u"", is_last=True, visited=None, actual_parent=None):
    """递归渲染 ASCII 树。

    Args:
        tree_nodes: build_tree 返回的节点列表（当前层级）
        status_by_id: id -> status map
        task_map: id -> task dict
        indent: 当前缩进前缀
        is_last: 当前节点是否是父节点的最后一个子节点
        visited: 用于检测循环引用
        actual_parent: 当前节点在树中的实际父节点 ID（None 表示为根）
    """
    if visited is None:
        visited = set()

    # 获取多父节点信息
    multi_parent_map = getattr(build_tree, "_multi_parent_map", {})

    for i, node in enumerate(tree_nodes):
        tid = node["id"]
        is_last_node = (i == len(tree_nodes) - 1)
        t = task_map.get(tid, {})
        status = t.get("status", "") if t else ""
        name = t.get("name", "") if t else ""

        # 状态图标
        if status in ("passed", "completed"):
            icon = u"✅"
        elif status == "failed":
            icon = u"❌"
        elif status == "in_progress":
            icon = u"\U0001F7E1"
        else:
            icon = u"⏳"

        # 选择连接符
        if is_last_node:
            connector = u"└── "
            child_indent = indent + u"    "
            if indent == u"" and not is_last:
                child_indent = u"│   "
        else:
            connector = u"├── "
            child_indent = indent + u"│   "

        # 状态文字
        status_text = status if status else u"unknown"

        # 当前任务标注
        extra = u""
        if status == "in_progress":
            extra = u"  ← 当前"

        # 多父节点标注：排除实际树中的父节点，只标注"额外"依赖
        parents = multi_parent_map.get(tid, [])
        if parents and actual_parent is not None:
            extra_parents = [p for p in parents if p != actual_parent and p in visited]
            if extra_parents:
                extra += u" [亦依赖 {0}]".format(u", ".join(extra_parents))

        # 输出行：包含状态图标
        line = u"{0}{1}{2} {3} {4} ({5}){6}".format(indent, connector, tid, icon, name, status_text, extra)
        u_print(line)

        # 递归子节点
        children = node.get("children", [])
        new_visited = visited | {tid}
        render_tree(children, status_by_id, task_map,
                    indent=child_indent, is_last=is_last_node, visited=new_visited,
                    actual_parent=tid)


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 新增功能 1：CLI 参数解析 + 改造后的 main
# ---------------------------------------------------------------------------

# ponytail: sys.argv over argparse, 4 flags don't need a framework

def parse_args(argv):
    """解析命令行参数。sys.argv 就够了。"""
    state_dir = None
    flags = {"summary": False, "tree": False, "json_output": False}
    for a in argv:
        if a == "--summary":
            flags["summary"] = True
        elif a == "--tree":
            flags["tree"] = True
        elif a == "--json":
            flags["json_output"] = True
        elif a.startswith("--"):
            pass
        elif state_dir is None:
            state_dir = a
    if state_dir is None:
        d = os.path.join(".claude", "animus")
        if os.path.exists(d):
            state_dir = d
        else:
            state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state")
    # 动态构造命名空间对象，兼容 Python 2/3
    ns = type("Args", (object,), {})()
    ns.state_dir = state_dir
    for k, v in flags.items():
        setattr(ns, k, v)
    return ns


def main():
    # 解析参数
    args = parse_args(sys.argv[1:])
    state_root = args.state_dir

    features_path = os.path.join(state_root, "features.json")

    if not os.path.exists(features_path):
        u_print(u"未找到 features.json: {0}".format(features_path))
        return 1

    data = read_json(features_path)
    tasks = get_tasks(data)
    status_by_id = {str(task.get("id", "")): str(task.get("status", "")) for task in tasks}
    task_map = {str(t.get("id", "")): t for t in tasks}

    total = len(tasks)
    passed = sum(1 for task in tasks if task.get("status") in ("passed", "completed"))
    passed_count = sum(1 for task in tasks if task.get("status") == "passed")
    completed_count = sum(1 for task in tasks if task.get("status") == "completed")
    failed_list = [task for task in tasks if task.get("status") == "failed"]
    in_progress = None
    for task in tasks:
        if task.get("status") == "in_progress":
            in_progress = task
            break
    pending_list = [task for task in tasks if task.get("status") == "pending"]

    executable_pending = [task for task in pending_list if can_run(task, status_by_id)]
    executable_pending.sort(key=lambda task: (-get_priority(task), str(task.get("id", ""))))
    next_pending = executable_pending[0] if executable_pending else None

    # 注入 state_root 到 render_summary 供 Oracle 验证门显示使用
    render_summary._state_root = state_root

    # --json 模式：只输出 JSON
    if args.json_output:
        # 构建树以获取 children 信息
        tree = build_tree(tasks, status_by_id)
        tree_children_map = {}

        def extract_children(nodes):
            for n in nodes:
                cids = [c["id"] for c in n.get("children", [])]
                tree_children_map[n["id"]] = cids
                extract_children(n.get("children", []))

        extract_children(tree)

        # 构建任务列表输出（保持有序）
        from collections import OrderedDict
        output_tasks = []
        for t in tasks:
            tid = str(t.get("id", ""))
            output_tasks.append(OrderedDict([
                ("id", tid),
                ("name", t.get("name", "")),
                ("status", t.get("status", "")),
                ("priority", get_priority(t)),
                ("depends_on", get_depends_on(t)),
                ("children", tree_children_map.get(tid, [])),
            ]))

        progress_pct = int(float(passed) / total * 100) if total > 0 else 0

        if total > 0 and passed == total:
            overall_status = u"completed"
        elif len(failed_list) > 0:
            overall_status = u"failed"
        elif in_progress is not None:
            overall_status = u"in_progress"
        else:
            overall_status = u"pending"

        # 阻塞链
        block_chains = compute_block_chains(tasks, status_by_id)

        output = OrderedDict([
            ("total", total),
            ("passed", passed),
            ("failed", len(failed_list)),
            ("in_progress", 1 if in_progress else 0),
            ("pending", len(pending_list)),
            ("progress_pct", progress_pct),
            ("status", overall_status),
            ("tasks", output_tasks),
            ("block_chains", block_chains),
        ])

        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        if sys.version_info[0] < 3:
            # Python 2: json.dumps 返回 str，需要 decode
            u_print(json_str.decode("utf-8") if isinstance(json_str, str) else json_str)
        else:
            u_print(json_str)
        return 0

    # --summary 模式
    if args.summary:
        render_summary(tasks, total, passed, len(failed_list), in_progress, len(pending_list))
        return 0

    # --tree 模式
    if args.tree:
        tree = build_tree(tasks, status_by_id)
        render_tree(tree, status_by_id, task_map)
        return 0

    # ponytail: --compact removed, --summary covers the use case

    # 默认模式：输出新格式看板（总览头 + 依赖树 + 阻塞链）
    render_summary(tasks, total, passed, len(failed_list), in_progress, len(pending_list))
    u_print(u"")

    tree = build_tree(tasks, status_by_id)
    # 状态图标映射
    _icons = {"passed": u"✅", "completed": u"✅", "failed": u"❌", "in_progress": u"\U0001F7E1"}
    # 根节点不用前缀渲染
    for i, node in enumerate(tree):
        tid = node["id"]
        t = task_map.get(tid, {})
        status = t.get("status", "") if t else ""
        name = t.get("name", "") if t else ""
        icon = _icons.get(status, u"⏳")
        cur = u"  ← 当前" if tid == (in_progress.get("id") if in_progress else None) else u""
        u_print(u"{0} {1} {2} ({3}){4}".format(tid, icon, name, status, cur))
        is_last_root = (i == len(tree) - 1)
        children = node.get("children", [])
        if children:
            if is_last_root:
                render_tree(children, status_by_id, task_map, indent=u"", is_last=True)
            else:
                render_tree(children, status_by_id, task_map, indent=u"│ ", is_last=False)

    block_chains = compute_block_chains(tasks, status_by_id)
    if block_chains:
        u_print(u"")
        u_print(u"阻塞链摘要:")
        for bc in block_chains[:5]:
            chain_parts = [bc["task_id"]] + bc["chain"]
            chain_str = u" ← ".join(chain_parts)
            u_print(u"  {0}  ({1} 层)".format(chain_str, bc["depth"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
