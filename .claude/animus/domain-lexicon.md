# 领域术语表

## 优先级分类
- **P0**: 阻断性问题，必须立即修复（版本不一致、文档严重过时、Python 2/3 写入 bug）
- **P1**: 重要问题，本周内修复（编号重复、表格格式、死代码、兼容性、路径匹配）
- **P2**: 文档同步问题（路线图状态、残留旧引用、文件名过时）

## 项目概念
- **Animus**: 本插件名称，状态机驱动的 AI 编码工作流引擎
- **四路路由**: `/animus-dev` 的四种开发路径（debug/fast/light/full），替代旧五路（已移除 oneshot）
- **PS1→Python 迁移**: 2026-07-04 完成的全仓库 PowerShell→Python 脚本迁移
- **Grilling**: 需求追问阶段，使用 AskUserQuestion 工具互动确认需求
- **feature-planner**: 将需求拆解为 features.json 可执行任务的 agent

## 技术模块
- **config.toml**: 两层配置系统（defaults → config.toml），取代旧三层 + project-config.json
- **memlog**: append-only 单一事件源持久化，位于 `.claude/animus/memlog/`
- **cmd_archive**: 归档引擎，将当前迭代打包到 `.claude/animus/archive/`
- **deferred_work**: 延期工作追踪，标记 defer 分诊的审查发现
- **hooks.json**: 4 种运行时钩子注册（PreToolUse/PostToolUse/PreCompact/Stop）
- **marketplace.json**: 插件市场发布配置，需与 plugin.json 版本同步
