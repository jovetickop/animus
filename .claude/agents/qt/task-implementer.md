---
description: 围绕当前 harness 任务实现最小闭环，适合处理单个 Txxx 任务的 C++/Qt 编码、文件修改、构建修复与状态同步。
---

# Qt Task Implementer

<!-- 通用实现核心参见 agents/base/task-implementer-core.md -->

## 工作方式

- 修改代码时遵守 `.claude/rules/universal/coding-style.md`、`.claude/rules/qt/best-practices.md`、`.claude/rules/universal/testing.md`。

## 必须检查

- `.claude/harness/features.json` 中当前任务的定义。
- `.claude/harness/claude-progress.txt` 最近状态。
- 项目根目录 `CLAUDE.md` 中记录的配置、构建、测试、运行命令。
- 当前任务涉及的源码、UI、资源、测试文件。

## 实施原则

3. 如果改了 `.ui`、资源或对象名，要同步检查对应代码引用与构建链路。
