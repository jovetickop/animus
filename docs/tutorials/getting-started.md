---
type: tutorial
audience: new-user
---

# 5 分钟上手 Animus

> Animus 是一个状态机驱动的 AI 编码工作流引擎。本文带你完成首次安装和使用。

---

## 学习目标

- 安装 Animus 插件
- 在目标项目中初始化 Animus 运行时
- 创建第一个开发任务
- 完成一个任务闭环

:::note[前置条件]

- **Claude Code** 已安装（Animus 是 Claude Code 插件）
- **Python 3.9+** — 引擎脚本依赖
- **Git** — 推荐用于版本控制
- **一个项目** — 任何语言的项目都可以

:::

---

## 第一步：安装插件

在 Claude Code 中运行：

```
/plugin install https://github.com/jovetickop/animus
```

或如果已发布到市场，通过插件市场安装。

---

## 第二步：初始化项目

在你的**目标项目根目录**中运行：

```
/animus-init
```

脚本会自动检测项目类型（C++/Qt、Rust、Go、Node.js、Python 等），创建 `.claude/animus/` 运行时目录，写入默认配置。

**执行内容：**
1. 检测项目根目录
2. 按项目文件判定语言栈
3. 创建 `.claude/animus/` 运行时目录
4. 写入 `config.toml` 项目配置
5. 生成空的 `features.json`

---

## 第三步：查看任务状态

```
/animus-status
```

如果初始化成功，会看到：

```
  Animus — 任务状态报告
  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  总任务数  : 0
  推荐下一步：/animus-dev — 开始第一个开发任务
```

---

## 第四步：开始第一个开发任务

```
/animus-dev
```

根据你描述的需求，AI 会自动选择合适的开发路径：

| 路径 | 适用场景 |
|------|---------|
| debug | bug 报告或异常 |
| fast | 1-2 文件的小改动 |
| light | 3-10 文件的新增功能 |
| full | 跨模块或架构级改动 |

AI 选路后会等待确认，然后创建任务、进入实现。

---

## 第五步：完成与审查

实现完成后：

1. 运行验证命令确保通过
2. 系统自动调用 **4 agent 并行审查**
3. 审查通过后任务标记为 `passed`

---

## 下一步

- 了解更多命令 → `docs/reference/commands.md`
- 查看当前任务 → `/animus-status`
- 有疑问 → `/animus-help`
