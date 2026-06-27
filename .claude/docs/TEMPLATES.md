# 模板目录角色说明

## 目录结构

```
.claude/templates/
├── state/               # 状态文件模板（安装到目标工程的 .claude/state/）
├── harness/             # 状态机脚本 + 配置模板（安装到目标工程的 .claude/harness/）
├── existing_project/    # 已有工程的 CLAUDE.md / review-checklist 模板
├── .clang-format        # C++ 格式化规则模板
├── .mcp.json            # MCP 服务器配置模板
└── init-project.ps1     # 项目初始化脚本（入口）
```

## state/ 模板文件

| 文件 | 用途 | 安装目标 |
|------|------|---------|
| `features.json` | 初始状态文件，包含示例任务 | `.claude/state/features.json` |
| `claude-progress.txt` | 进度日志初始文件（空占位） | `.claude/state/claude-progress.txt` |

**注意：** `features.active.json` 和 `features.archive.json` 已合并清理。`features.json` 是唯一的初始状态模板。

## harness/ 脚本文件

| 文件 | 用途 |
|------|------|
| `update-progress.ps1` | 状态机主入口（薄编排器，模块在 modules/） |
| `modules/validate-transition.ps1` | 状态转换校验 |
| `modules/oracle-runner.ps1` | Oracle 验证（构建/测试） |
| `modules/report-generator.ps1` | 报告生成 |
| `modules/task-helpers.ps1` | 任务辅助 |
| `modules/git-helper.ps1` | Git 操作 |
| `run-regression.ps1` | 一键构建+测试 |
| `coding-session.ps1` | 会话入口 |
| `init.ps1` | 首次初始化引导 |
| `show-status.py` | 状态显示 |
| `project-config.json` | 项目类型配置 |
| `features.json` | 状态文件模板 |

## 安装流程

`init-project.ps1` 按以下顺序处理：
1. 检测项目类型（CMake/Cargo/npm/pip/go）
2. 创建 `.claude/` 目录结构
3. 从 `templates/harness/` 复制状态机脚本
4. 从 `templates/state/` 复制状态文件
5. 合并 `CLAUDE.md`（追加式，不覆盖）
