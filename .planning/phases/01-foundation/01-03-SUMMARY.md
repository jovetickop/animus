# Phase 01 Plan 03: features.json 路径标准化 Summary

## 执行结果

**Plan:** 01-03 - 统一 features.json 路径为 .claude/state/
**Phase:** foundation
**Wave:** 2
**Requirement:** TECHD-04
**Commit:** 13fff41

## 目标

消除 8 个脚本中的双重查找逻辑（.claude/harness/ 和 .claude/state/），统一使用 .claude/state/ 作为 features.json 的唯一标准路径。

## 执行摘要

经过逐文件审查，发现**实际只有 3 个文件需要修改**（而非 8 个）：

| 文件 | 修改前 | 修改后 |
|------|--------|--------|
| pre-compact.ps1 | dual-path fallback (harness → state) | 仅用 state，添加 deprecated 警告 |
| pre-compact.sh | dual-path fallback (harness → state) | 仅用 state，添加 deprecated 警告 |
| session-catchup.py | 3 个候选路径含 harness | 仅用 state |

其余 5 个文件（pre-tool-use.ps1, pre-tool-use.sh, stop-check.ps1, stop-check.sh, clang-format.ps1）已经是单路径实现，无需修改。

show-status.py 使用 state 路径，也无需修改。

## 修改详情

### pre-compact.ps1
- 移除了 `foreach ($sub in @("harness", "state"))` 双重路径循环
- 移除了 `$progressPath` 的 harness 回退逻辑
- 添加了旧路径检测和 deprecation 警告

### pre-compact.sh
- 移除了 `for sub in harness state` 双重路径循环
- 移除了 `$progress_path` 的 harness 回退逻辑
- 添加了旧路径检测和 deprecation 警告

### session-catchup.py
- 移除了 features_candidates 列表中的 harness 和根目录候选
- 仅保留 `.claude/state/features.json`

## 验证结果

| 验证项 | 结果 |
|--------|------|
| 语法检查 (PowerShell) | PASS - 4 个脚本全部通过 |
| 语法检查 (Shell) | PASS - 3 个脚本全部通过 |
| 语法检查 (Python) | PASS - 2 个脚本全部通过 |
| dual-path fallback 逻辑 | CLEAN - 无残留 |
| 代码级 harness/features.json 引用 | 仅存在于 deprecated 警告中（符合要求） |

## 验证命令

```bash
# 检查无旧路径代码残留（仅允许注释/deprecation 警告）
git grep "\.claude/harness/features\.json" -- "*.ps1" "*.sh" "*.py" | grep -v "#" | grep -v "deprecated" | grep -v "WARNING"

# 确认 dual-path fallback 逻辑已清除
grep -rn "for.*harness.*state\|foreach.*harness.*state" .claude/hooks/scripts/ .claude/scripts/
```

## TDD Gate 合规

本计划不涉及 TDD，实现类任务无 TDD 要求。

## 后续影响

此变更可能导致：
1. 已在旧路径 (.claude/harness/) 有 features.json 的项目会看到 deprecated 警告
2. session-catchup.py 的恢复报告会更准确（只报告 state 路径的状态）

建议用户运行 harness-code-setup 迁移脚本将旧路径文件迁移到新路径。

## Self-Check: PASSED

- [x] commit 13fff41 存在
- [x] 3 个文件已修改
- [x] 语法检查全部通过
- [x] dual-path fallback 逻辑已清除