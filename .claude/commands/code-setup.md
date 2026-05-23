---
description: 把工作流资产接入已有 C++/Qt 仓库
---

请用 /code-setup 初始化当前工作目录。

## 目标

- 安装 `.claude/harness/`，让项目可以跨会话保存任务状态。
- 自动探索可执行的"配置/构建/测试/运行"命令，并写入项目根目录 `CLAUDE.md`。
- 不要覆盖已有源码树。

## 模板源目录

先识别模板源目录（模板仓库根目录，且其下应存在 `.claude/templates/`），优先从以下位置查找：

- `./`（当前仓库根目录，适用于已把 `.claude` 拷入目标工程）
- `./ty-qt-ai-plugin/`
- 用户在指令中明确给出的模板目录（若给的是 `.claude/` 目录，自动归一到其上一级仓库根目录）

如果已经找到模板源目录，就直接从该目录一次性完成落位，不要要求用户自己逐个复制文件。

模板资产默认位于模板源目录下的 `.claude/`。

## 自动探索命令（必须执行）

始终执行以下步骤：

1. 收集候选命令：
   - 优先读取 `CMakePresets.json`、`CMakeUserPresets.json`
   - 读取已有脚本（如 `build*.ps1`、`build*.bat`、`test*.ps1`、`test*.bat`）
   - 回退候选：
     - 配置：`cmake -S . -B build`
     - 构建：`cmake --build build --config Debug`
     - 测试：`ctest --test-dir build -C Debug --output-on-failure`
2. 用真实命令探测可用性，至少验证一次配置和构建命令。
3. 有测试入口时，至少执行一次测试或 smoke test。
4. 将最终命令写入 `CLAUDE.md` 的"自动识别命令"区块，禁止留空占位符。
5. 检查当前目录是否为 Git 仓库（`git rev-parse --is-inside-work-tree`）。
6. 如果某项无法探测成功，写明失败原因、已尝试命令和推荐下一步。

## 接入步骤

1. 识别主 `CMakeLists.txt`、目标名、Qt 版本和当前测试入口。
2. 从 `.claude/templates/harness/` 复制 `.claude/harness/`。
3. 复制 `.claude/templates/existing_project/CLAUDE.md`，并填入实际构建与测试命令。
4. 复制 `.claude/templates/existing_project/review-checklist.md` 与 `.claude/templates/existing_project/cmake-adapter.md`。
5. 将模板仓库中的 `.claude/rules/`、`.claude/commands/`、`.claude/hooks/` 分别复制为项目内的 `.claude/rules/`、`.claude/commands/`、`.claude/hooks/`。
6. 不要替换现有应用源码、UI 文件或目录结构。
7. 自动探索"配置/构建/测试/运行"命令，并写入根目录 `CLAUDE.md`。
8. 输出一份自动识别不到的信息清单，提示人工补充。

## 输出要求

始终报告：

- 已复制或生成的文件
- 构建命令
- 测试命令
- 运行命令
- 是否启用"任务完成后自动提交并推送"（或因非 Git 仓库而跳过）
- 探测是否已真实执行（成功/失败）
- 需要人工确认的事项

## 安全规则

- 未经明确同意，不要覆盖已有工程中的 `src/`、`include/`、`ui/`、`tests/`。
- 如果仓库同时存在 Qt Widgets 与 QML 结构，优先保持现状，不要混改架构。
- 如果项目里已有 `.claude/` 内容，合并时必须保留不相关配置。
