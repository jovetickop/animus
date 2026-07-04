#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 2.7+ / 3.x 兼容
"""
plugin-validator.py — 插件自身完整性验证器

确定性验证：8 条硬规则检查插件结构完整性。
与 BMAD validate-skills.js 思想一致，但适配 animus 的插件结构。

用法：
    python scripts/plugin-validator.py              # 人类可读输出
    python scripts/plugin-validator.py --strict     # CI 模式，warning 也 exit 1
    python scripts/plugin-validator.py --json       # JSON 输出
    python scripts/plugin-validator.py --fix        # 自动修复简单问题
"""

from __future__ import print_function, unicode_literals
import fnmatch
import json
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# 规则引擎
# ============================================================

class Finding(object):
    """单条验证结果"""
    def __init__(self, rule, severity, message, file_path=""):
        self.rule = rule
        self.severity = severity  # "error" or "warning"
        self.message = message
        self.file_path = file_path

    def to_dict(self):
        return {"rule": self.rule, "severity": self.severity,
                "message": self.message, "file": self.file_path}

    def __str__(self):
        tag = "ERROR" if self.severity == "error" else "WARNING"
        loc = " [{0}]".format(self.file_path) if self.file_path else ""
        return "  [{0}][{1}]{2} {3}".format(tag, self.rule, loc, self.message)


def _read_file(path):
    """读取文件内容，兼容 Python 2/3"""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read().decode("utf-8", errors="replace")


def _parse_frontmatter(text):
    """解析 YAML frontmatter，返回 dict"""
    if not text:
        return {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    yaml_text = m.group(1)
    result = {}
    for line in yaml_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


# ============================================================
# 规则实现
# ============================================================

def check_r1_plugin_commands(plugin_path):
    """R1: plugin.json 引用的 commands 文件都存在"""
    findings = []
    text = _read_file(plugin_path)
    if not text:
        return [Finding("R1", "error", "plugin.json 不存在", plugin_path)]

    try:
        data = json.loads(text)
    except Exception as e:
        return [Finding("R1", "error", "plugin.json JSON 解析失败: {0}".format(e), plugin_path)]

    commands = data.get("commands", [])
    for cmd_path in commands:
        full_path = os.path.join(PROJECT_ROOT, cmd_path)
        if not os.path.exists(full_path):
            findings.append(Finding("R1", "error",
                                    "命令文件不存在: {0}".format(cmd_path), full_path))
    return findings


def check_r2_agent_frontmatter(agents_dir):
    """R2: 所有 Agent 定义文件有 name + description"""
    findings = []
    if not os.path.isdir(agents_dir):
        return [Finding("R2", "warning", "agents/ 目录不存在", agents_dir)]

    for root, dirs, files in os.walk(agents_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            # 跳过任务方案文档等非 agent 定义文件
            filepath = os.path.join(root, f)
            relpath = os.path.relpath(filepath, PROJECT_ROOT)
            text = _read_file(filepath)
            if not text:
                continue
            fm = _parse_frontmatter(text)
            if not fm.get("name"):
                findings.append(Finding("R2", "error",
                                        "缺少 frontmatter name", relpath))
            desc = fm.get("description", "")
            if not desc:
                findings.append(Finding("R2", "error",
                                        "缺少 frontmatter description", relpath))
            elif len(desc) < 10:
                findings.append(Finding("R2", "warning",
                                        "description 过短({0}字)".format(len(desc)), relpath))
    return findings


def check_r3_hooks_scripts(hooks_path):
    """R3: hooks.json 注册的脚本文件存在"""
    findings = []
    text = _read_file(hooks_path)
    if not text:
        return [Finding("R3", "error", "hooks.json 不存在", hooks_path)]

    try:
        data = json.loads(text)
    except Exception as e:
        return [Finding("R3", "error", "hooks.json JSON 解析失败: {0}".format(e), hooks_path)]

    hooks = data.get("hooks", {})
    for event_name, hook_list in hooks.items():
        for entry in hook_list:
            hooks_inner = entry.get("hooks", [])
            for h in hooks_inner:
                cmd = h.get("command", "")
                # 提取所有 ${CLAUDE_PLUGIN_ROOT}/ 路径
                for m in re.finditer(r'\$\{CLAUDE_PLUGIN_ROOT\}/([^\s"\']+)', cmd):
                    script_rel = m.group(1)
                    script_full = os.path.join(PROJECT_ROOT, script_rel)
                    if not os.path.exists(script_full):
                        findings.append(Finding("R3", "error",
                                                "脚本不存在: {0}".format(script_rel), script_rel))
    return findings


def check_r4_agent_index(agents_dir, index_path):
    """R4: agent-index.md 中的 Agent 与 agents/ 目录一一对应"""
    findings = []
    # 收集 agents/ 下所有 agent 定义文件（排除 base/ 核心模板）
    agent_names = set()
    if os.path.isdir(agents_dir):
        for root, dirs, files in os.walk(agents_dir):
            for f in files:
                if not f.endswith(".md"):
                    continue
                # 排除 base/ 下的核心模板文件
                rel_dir = os.path.relpath(root, agents_dir)
                if rel_dir.startswith("base"):
                    continue
                agent_names.add(f.replace(".md", ""))

    text = _read_file(index_path)
    if not text:
        return [Finding("R4", "warning", "agent-index.md 不存在", index_path)]

    # 检查 index 中出现的 agent 文件引用
    indexed = set()
    for m in re.finditer(r'`([a-z0-9_-]+)`', text):
        indexed.add(m.group(1))

    # 不在 index 中的 agent
    for name in sorted(agent_names):
        if name not in indexed:
            findings.append(Finding("R4", "warning",
                                    "Agent 未在 agent-index.md 中记录: {0}".format(name), name))
    return findings


def check_r5_rule_frontmatter(rules_dir):
    """R5: rules/ 下所有 .md 文件有合法 frontmatter"""
    findings = []
    if not os.path.isdir(rules_dir):
        return [Finding("R5", "warning", "rules/ 目录不存在", rules_dir)]

    for root, dirs, files in os.walk(rules_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            filepath = os.path.join(root, f)
            relpath = os.path.relpath(filepath, PROJECT_ROOT)
            text = _read_file(filepath)
            if not text:
                findings.append(Finding("R5", "error", "文件为空", relpath))
                continue
            fm = _parse_frontmatter(text)
            if not fm:
                findings.append(Finding("R5", "warning",
                                        "缺少 YAML frontmatter", relpath))
    return findings


def check_r6_description_overlap(agents_dir):
    """R6: 同语言组内 description 不应显著重叠（简化版，仅标记重复片段）"""
    findings = []
    if not os.path.isdir(agents_dir):
        return findings
    descs = []
    for root, dirs, files in os.walk(agents_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            filepath = os.path.join(root, f)
            text = _read_file(filepath)
            if not text:
                continue
            fm = _parse_frontmatter(text)
            desc = fm.get("description", "")
            if desc:
                relpath = os.path.relpath(filepath, PROJECT_ROOT)
                descs.append((relpath, desc))
    # 简单检查：如果有两个 description 完全相同，标记
    seen = {}
    for path_, desc_ in descs:
        if desc_ in seen:
            findings.append(Finding("R6", "warning",
                                    "description 与 {0} 相同".format(seen[desc_]), path_))
        seen[desc_] = path_
    return findings


def check_r7_orphan_files(agents_dir, rules_dir):
    """R7: 检查 agents/ 和 rules/ 中的文件是否被引用"""
    findings = []
    all_md_files = set()
    for d in [agents_dir, rules_dir]:
        if os.path.isdir(d):
            for root, dirs, files in os.walk(d):
                for f in files:
                    if f.endswith(".md"):
                        all_md_files.add(os.path.join(root, f))

    # 收集所有引用（扫描 docs/ 下所有 .md + CLAUDE.md）
    referenced = set()
    doc_sources = ["CLAUDE.md"]
    docs_dir = os.path.join(PROJECT_ROOT, "docs")
    if os.path.isdir(docs_dir):
        for root, dirs, files in os.walk(docs_dir):
            for f in files:
                if f.endswith(".md"):
                    doc_sources.append(os.path.relpath(
                        os.path.join(root, f), PROJECT_ROOT))
    for doc_path in doc_sources:
        full = os.path.join(PROJECT_ROOT, doc_path)
        text = _read_file(full)
        if text:
            for m in re.finditer(r'`([a-z0-9_/.-]+)`', text):
                ref = m.group(1)
                for md_f in all_md_files:
                    if ref in md_f:
                        referenced.add(md_f)

    for fpath in sorted(all_md_files):
        if fpath not in referenced:
            rel = os.path.relpath(fpath, PROJECT_ROOT)
            findings.append(Finding("R7", "warning", "可能未被引用的文件", rel))
    return findings


def check_r8_config_keys(config_py_path, config_toml_path):
    """R8: config_loader.py 中的配置键在 config.toml 中有声明"""
    findings = []
    text = _read_file(config_py_path)
    if not text:
        return [Finding("R8", "warning", "config_loader.py 不存在", config_py_path)]

    # 提取 DEFAULT_CONFIG 中的键
    keys_in_code = set()
    in_defaults = False
    for line in text.split("\n"):
        if "DEFAULT_CONFIG" in line:
            in_defaults = True
        if in_defaults:
            m = re.match(r'\s+"(\w+)":', line)
            if m:
                keys_in_code.add(m.group(1))
        if in_defaults and line.strip() == "}":
            break

    toml_text = _read_file(config_toml_path)
    if not toml_text:
        return [Finding("R8", "warning", "config.toml 模板不存在", config_toml_path)]

    for key in sorted(keys_in_code):
        if key not in toml_text:
            findings.append(Finding("R8", "warning",
                                    "配置键 '{0}' 在 config.toml 中无声明".format(key), config_toml_path))
    return findings


# ============================================================
# 输出
# ============================================================

def print_human(findings, strict):
    """人类可读输出"""
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    for f in findings:
        print(f)

    if not findings:
        print(u"PASSED: 全部检查通过")
        return True

    if errors:
        print(u"\nFAILED: {0} 个错误".format(len(errors)))
    if warnings and strict:
        print(u"\nFAILED (--strict): {0} 个警告".format(len(warnings)))
    elif warnings:
        print(u"\n通过但有 {0} 个警告".format(len(warnings)))
    return len(errors) == 0 and (not strict or len(warnings) == 0)


def print_json(findings, strict, passed):
    """JSON 输出"""
    result = {
        "version": "1.0",
        "passed": passed,
        "strict": strict,
        "total_findings": len(findings),
        "errors": len([f for f in findings if f.severity == "error"]),
        "warnings": len([f for f in findings if f.severity == "warning"]),
        "findings": [f.to_dict() for f in findings],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return passed


# ============================================================
# 入口
# ============================================================

def run():
    """执行全部 8 条规则"""
    args = sys.argv[1:]
    strict = "--strict" in args
    json_output = "--json" in args
    fix_mode = "--fix" in args

    findings = []

    # R1
    plugin_path = os.path.join(PROJECT_ROOT, ".claude-plugin", "plugin.json")
    findings.extend(check_r1_plugin_commands(plugin_path))

    # R2
    agents_dir = os.path.join(PROJECT_ROOT, "agents")
    findings.extend(check_r2_agent_frontmatter(agents_dir))

    # R3
    hooks_path = os.path.join(PROJECT_ROOT, "hooks", "hooks.json")
    findings.extend(check_r3_hooks_scripts(hooks_path))

    # R4
    index_path = os.path.join(PROJECT_ROOT, "docs", "agent-index.md")
    findings.extend(check_r4_agent_index(agents_dir, index_path))

    # R5
    rules_dir = os.path.join(PROJECT_ROOT, "rules")
    findings.extend(check_r5_rule_frontmatter(rules_dir))

    # R6
    findings.extend(check_r6_description_overlap(agents_dir))

    # R7
    findings.extend(check_r7_orphan_files(agents_dir, rules_dir))

    # R8
    config_py = os.path.join(PROJECT_ROOT, "scripts", "config_loader.py")
    config_toml = os.path.join(PROJECT_ROOT, ".claude", "animus", "config.toml")
    findings.extend(check_r8_config_keys(config_py, config_toml))

    # 自动修复（R2: 补 description）
    if fix_mode:
        for f in findings:
            if f.rule == "R2" and f.severity == "error" and "description" in f.message:
                filepath = os.path.join(PROJECT_ROOT, f.file_path)
                text = _read_file(filepath)
                if text and "description:" not in text:
                    # 在 name 行后追加 description
                    name_tag = 'name:'
                    if name_tag in text:
                        name_end = text.index(name_tag) + len(name_tag)
                        line_end = text.index('\n', name_end)
                        insertion = '\ndescription: "TBD -- please fill"'
                        new_text = text[:line_end] + insertion + text[line_end:]
                    try:
                        with open(filepath, "wb") as fh:
                            fh.write(new_text.encode("utf-8"))
                        print(u"[已修复] {0}: 补全 description".format(f.file_path))
                    except Exception as e:
                        print(u"[修复失败] {0}: {1}".format(f.file_path, e))

    passed = print_human(findings, strict) if not json_output else True
    if json_output:
        passed = print_json(findings, strict, passed)
    return passed


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
