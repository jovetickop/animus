# CodeHarness

`CodeHarness` 是一个 Claude Code 技能，面向**需要多轮编码会话的复杂任务**。输入 PRD+方案文档，自动拆解为可执行任务列表，按状态机逐个推进，验收后提交。支持 C++/Qt、Python、Node.js、Rust。

- **状态化执行**：每个任务有严格的状态流转（pending → in_progress → passed/failed）
- **插件化架构**：自动检测项目类型，按需激活对应语言插件
- **跨会话持久化**：Harness 状态引擎记录进度，断点续传

## 安装

```bash
git clone https://github.com/jovetickop/CodeHarness.git ~/.claude/skills/code-harness
```

## 使用

在任意项目中执行：

```
/code-harness
```

技能会自动检测项目状态：
- 首次使用 → 初始化 harness 并检测项目类型
- 已有进度 → 读取状态，引导下一步

## 工作流

```
人工: 输入 PRD/需求
  → AI: /code-plan 生成 features.json
    → AI: 选任务并标记 in_progress
      → AI: 实现 + 构建/测试
        → AI: /code-check 验收
          → 通过 → 标记 passed → 提交 → 下一个
          → 失败 → 标记 failed → 重试
```

## 目录结构

```
CodeHarness/
├── SKILL.md                      ← 技能入口
├── agents/
│   ├── universal/                ← 通用 Agent（所有项目）
│   ├── qt/                       ← C++/Qt 插件
│   ├── python/                   ← Python 插件
│   ├── node/                     ← Node.js 插件
│   └── rust/                     ← Rust 插件
├── commands/                     ← 斜杠命令（code-setup, code-plan, code-check）
├── rules/
│   ├── universal/                ← 通用规范
│   ├── qt/                       ← Qt 专项规范
│   ├── python/                   ← Python 规范
│   ├── node/                     ← Node.js 规范
│   └── rust/                     ← Rust 规范
├── hooks/                        ← 自动化钩子（clang-format）
├── skills/
│   └── tdd-workflow/             ← TDD 工作流技能
└── templates/
    ├── harness/                  ← 状态引擎（复制到目标项目）
    └── existing_project/         ← 项目初始化模板
```

## 支持的项目类型

| 类型 | 检测方式 | 激活的插件 |
|------|---------|-----------|
| C++/Qt | CMakeLists.txt + find_package(Qt | agents/qt/ + rules/qt/ |
| C++ (纯 CMake) | CMakeLists.txt 不含 Qt | rules/cpp-cmake/ |
| Python | pyproject.toml / requirements.txt | agents/python/ + rules/python/ |
| Node.js | package.json | agents/node/ + rules/node/ |
| Rust | Cargo.toml | agents/rust/ + rules/rust/ |
| 通用 | 以上都无 | 仅 universal/ |

## 统计

| 类别 | 数量 |
|------|------|
| Agent 定义 | 16（5 universal + 4 qt + 2 python + 3 node + 2 rust） |
| 规则文件 | 8（3 universal + 2 qt + 1 python + 1 node + 1 rust） |
| 斜杠命令 | 3 |
| 技能 | 2（code-harness + tdd-workflow） |
| Harness 脚本 | 12 |
