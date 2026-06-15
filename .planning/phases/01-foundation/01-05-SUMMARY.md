---
phase: "01-foundation"
plan: "05"
subsystem: "infrastructure"
tags: ["git", "editorconfig", "line-endings", "encoding", "standardization"]
dependency_graph:
  requires:
    - "01-01"
    - "01-02"
    - "01-04"
  provides:
    - "infrastructure:git-attributes"
    - "infrastructure:editor-config"
  affects:
    - "仓库根目录"
tech_stack:
  added: ["Git attributes", "EditorConfig"]
  patterns: ["Line ending standardization", "Encoding normalization"]
key_files:
  created:
    - ".gitattributes"
    - ".editorconfig"
decisions:
  - id: "01-05-D1"
    decision: "PowerShell 脚本使用 CRLF，Shell/Python/JSON 使用 LF"
    rationale: "Windows PowerShell 5.1 传统要求 CRLF；跨平台脚本统一使用 LF"
  - id: "01-05-D2"
    decision: "二进制文件声明为 binary 防止换行符转换"
    rationale: "图片、PDF、exe 等二进制文件不应被 Git 转换"
---

# Phase 01 Plan 05: 基础设施标准化 Summary

## 执行概要

成功创建 `.gitattributes` 和 `.editorconfig` 两个基础设施文件，确保仓库长期一致的换行符和编辑器行为。

## 已完成任务

| Task | 名称 | Commit | 文件 |
| ---- | ---- | ------- | ---- |
| 1 | 创建 .gitattributes | 45d29c3 | .gitattributes |
| 2 | 创建 .editorconfig | 45d29c3 | .editorconfig |
| 3 | git add --renormalize | 45d29c3 | - |

## 关键变更

### .gitattributes
- `* text=auto` 自动检测文本文件
- `*.sh/*.bash` → `eol=lf` (Unix shell 要求)
- `*.ps1/*.psd1/*.psm1/*.bat/*.cmd` → `eol=crlf` (Windows PowerShell)
- `*.py/*.json/*.yaml/*.md/*.toml/*.ini` → `eol=lf` (跨平台源文件)
- `*.png/*.jpg/*.pdf/*.exe/*.dll/*.ico` → `binary` (不转换)

### .editorconfig
- `root = true` 顶层配置
- `charset = utf-8`, `end_of_line = lf` 全局默认
- `[*.ps1]` → `end_of_line = crlf`
- `[*.sh]` → `end_of_line = lf`
- `[*.{json,yaml,yml,toml}]` → `indent_size = 2`
- `[*.py]` → `indent_size = 4`

## 验证结果

```bash
$ ls -la .gitattributes .editorconfig
-rw-r--r-- .gitattributes    (已提交)
-rw-r--r-- .editorconfig      (已提交)

$ git status --short
?? tmp/  (临时目录，来自之前操作)
```

## 偏差记录

无偏差 - 计划完全按规格执行。

## 后续影响

- 所有 `.sh` 文件将统一为 LF 换行符
- 所有 `.ps1` 文件将统一为 CRLF 换行符
- 编辑器打开文件时自动应用对应编码和缩进规则
- 新成员克隆仓库后无需手动配置编辑器