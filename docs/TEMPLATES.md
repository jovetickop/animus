# 模板目录角色说明

## 目录结构

```
templates/
├── harness/             # 状态机脚本 + 配置模板（安装到目标工程的 .claude/harness-cc/）
├── existing_project/    # 已有工程模板（review-checklist / cmake-adapter）
├── .clang-format        # C++ 格式化规则模板
├── .mcp.json            # MCP 服务器配置模板
└── init-project.ps1     # 项目初始化脚本（入口）
```

**说明：** 旧版 `state/` 目录已合并到 `harness/`，不再单独存放状态模板。
安装目标路径统一为 `.claude/harness-cc/`（不再使用 `.claude/harness/` 和 `.claude/state/`）。

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
2. 创建 `.claude/harness-cc/` 运行时目录
3. 从 `templates/harness/` 复制状态机脚本和初始模板
4. 回填检测到的构建/测试命令到 `project-config.json`
5. **不再修改目标项目的 CLAUDE.md**（Agent 通过 `${CLAUDE_PLUGIN_ROOT}` 从技能安装目录加载）
