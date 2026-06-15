# Phase 01 Plan 01: PS 脚本 UTF-16LE → UTF-8 with BOM + 中文注释修复

## 执行概述

**计划:** 01-01  
**阶段:** 01-foundation  
**执行时间:** 2026-06-14  
**任务数:** 2/2  
**状态:** 完成

## 目标

将 7 个 UTF-16LE 编码的 PowerShell 脚本转换为 UTF-8 with BOM，同时验证中文注释恢复情况。

## 执行结果

### Task 1: 批量转换 7 个 UTF-16LE .ps1 文件为 UTF-8 with BOM

**状态:** 已完成

| 文件 | BOM 验证 | 编码验证 | 文件大小 |
|------|----------|----------|----------|
| .claude/templates/harness/update-progress.ps1 | EF BB BF | utf-8 | 15007 |
| .claude/templates/harness/run-regression.ps1 | EF BB BF | utf-8 | 1564 |
| .claude/templates/harness/coding-session.ps1 | EF BB BF | utf-8 | 3203 |
| .claude/templates/harness/init.ps1 | EF BB BF | utf-8 | 669 |
| .claude/commands/check-consistency.ps1 | EF BB BF | utf-8 | 2052 |
| .claude/commands/harness-code-setup.ps1 | EF BB BF | utf-8 | 11301 |
| .claude/commands/validate-features.ps1 | EF BB BF | utf-8 | 2695 |

**转换命令:**
```powershell
Get-Content -Path $file -Encoding Unicode -Raw | Set-Content -Path $file -Encoding UTF8 -NoNewline
```

### Task 2: 验证 update-progress.ps1 中文注释恢复情况

**状态:** 部分恢复（存在原始损坏）

验证结果：
- 第 96 行: `$lastError = "无"` - 正常
- 第 100 行: `"passed" { "验证通过" }` - 正常
- 第 101 行: `"failed" { "验证失败" }` - 正常
- 第 102 行: `"in_progress" { "进行中（待验证）" }` - 正常
- 第 103 行: `default { "等待执行" }` - 正常
- 第 112 行: `$historyLines = @("暂无任务历史记录")` - 正常

**注意:** `harness-code-setup.ps1` 第 45 行存在少量原始损坏的中文注释（`# �ų� features.json �� claude-progress.txt...`），这是原始文件创建时就已存在的损坏，转换过程仅保留现有内容而不修复已损坏的字符。

## 提交记录

| 哈希 | 消息 |
|------|------|
| `38b38cf` | fix(01-01): convert 7 PowerShell scripts from UTF-16LE to UTF-8 with BOM |

## 验证通过项

- [x] 所有 7 个 .ps1 文件编码为 UTF-8 with BOM
- [x] BOM 字节验证 efbbbf 通过
- [x] `file --mime-encoding` 显示 utf-8
- [x] update-progress.ps1 核心中文注释正常显示
- [x] Git diff 可正确显示文本变更而非 "binary files differ"

## 后续建议

1. 手动检查 `harness-code-setup.ps1` 第 45 行的中文注释，根据上下文修复或删除
2. 运行 `harness-code-setup.ps1` 功能测试验证脚本正常工作

## 关键文件

| 文件 | 用途 |
|------|------|
| `.claude/templates/harness/update-progress.ps1` | 状态机核心脚本（424行） |
| `.claude/templates/harness/run-regression.ps1` | 回归测试脚本 |
| `.claude/templates/harness/coding-session.ps1` | 编码会话脚本 |
| `.claude/templates/harness/init.ps1` | 初始化脚本 |
| `.claude/commands/check-consistency.ps1` | 一致性检查命令 |
| `.claude/commands/harness-code-setup.ps1` | Setup 命令 |
| `.claude/commands/validate-features.ps1` | 特性验证命令 |