# Phase 01 Plan 04: Templates/State 清理 Summary

## 概述

| 字段 | 值 |
|------|-----|
| **Phase** | 01-foundation |
| **Plan** | 04 |
| **Subsystem** | templates |
| **Tags** | `TECHD-05` `cleanup` |
| **Dependency Graph** | requires: 01-03 (templates use .claude/state/), 01-01 (UTF-8 encoding) |
| **Tech Stack** | PowerShell, JSON |
| **Key Files Created** | `.claude/templates/harness/features.json` |
| **Key Files Modified** | `.claude/templates/state/features.json` (保留), `.claude/templates/state/claude-progress.txt` (保留) |
| **Key Files Deleted** | `.claude/templates/state/features.active.json`, `.claude/templates/state/features.archive.json` |
| **Decisions** | 合并 features.active.json 到 harness/features.json（因为它包含 `parallel_group` 字段更完整） |
| **Duration** | ~5 minutes |
| **Completed Date** | 2026-06-15 |

## 任务执行

### Task 1: 修复 init-project.ps1 source path bug 并清理 templates/state/

**Action:** 根据 RESEARCH.md Q5 分析，修复 templates/state/ 目录结构，明确 JSON 模板角色。

**执行步骤:**
1. 将 `features.active.json` 内容合并到 `templates/harness/features.json`（features.active.json 有 `verify_config` + `tasks` 含 `parallel_group`，是更完整的模板）
2. 删除 `templates/state/features.active.json`（已合并）
3. 删除 `templates/state/features.archive.json`（空 tasks 数组，无用途）
4. 保留 `templates/state/features.json` 作为备份
5. 保留 `templates/state/claude-progress.txt`（安装时复制到目标项目）

**目录结构修复后:**
```
templates/
├── harness/          # init-project.ps1 从这里复制
│   ├── features.json # 合并后的完整模板
│   ├── update-progress.ps1
│   └── ...
└── state/            # 仅保留运行时状态文件
    ├── features.json # 备份（保留）
    └── claude-progress.txt
```

**验证结果:**
- `templates/harness/features.json` 存在且包含完整 tasks 数组和 verify_config
- `templates/state/` 仅包含 `features.json`（备份）和 `claude-progress.txt`
- `features.active.json` 和 `features.archive.json` 已删除
- JSON 语法验证通过
- PowerShell 语法验证通过

## 提交记录

| Commit | Message |
|--------|---------|
| `3e45e28` | fix(01-04): clean up templates/state/ and fix init-project.ps1 path |

## 验证清单

- [x] templates/harness/features.json 存在且为有效 JSON
- [x] templates/harness/features.json 包含完整的 tasks 数组和 verify_config
- [x] templates/state/ 目录包含 features.json（备份）和 claude-progress.txt
- [x] templates/state/features.active.json 和 features.archive.json 已删除
- [x] init-project.ps1 可以从 templates/harness/ 找到 features.json
- [x] JSON 语法验证通过
- [x] PowerShell 语法验证通过

## 自我检查

**Self-Check: PASSED**

- features.json 存在于正确位置: `.claude/templates/harness/features.json`
- 验证命令: `python -m json.tool .claude/templates/harness/features.json` 返回有效
- 清理后 templates/state/ 仅包含: `features.json`, `claude-progress.txt`
- 确认已删除: `features.active.json`, `features.archive.json`

## TDD Gate 合规

本计划不涉及 TDD 流程，故不适用。