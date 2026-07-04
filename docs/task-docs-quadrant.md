---
type: reference
audience: plugin-developer
---

# 文档四象限重组（Docs Quadrant Restructure）

> 将现有 `docs/` 按 Diátaxis 四象限（Tutorials / How-To / Explanation / Reference）重组，
> 让用户和 AI 都能快速定位正确的文档。
> 参考 BMAD Method 文档站的象限组织模式。

---

## 1. 背景与动机

### 现状

当前 `docs/` 目录：

```
docs/
  agent-index.md              ← 参考/索引
  architecture.md             ← 解释/架构
  bmad-optimization-roadmap.md  ← 规划/路线图
  guide.md                    ← 混合体：用户指南 + 底层机制（~600 行）
  reports/                    ← 运行时报告
```

核心问题：

| 问题 | 表现 | 影响 |
|------|------|------|
| `guide.md` 混合两类读者 | 前段是用户操作手册，后段是架构解析 | 新用户翻半天找不到"怎么开始"，开发者要翻过用户手册才能找设计原理 |
| 缺少教程入口 | 没有 `getting-started.md` | 新用户第一印象是"好大一坨文档，从哪看？" |
| 缺少 how-to 目录 | "如何新增 Agent""如何配置审查"散落在各处 | 有明确目标的人需要全文搜索 |
| 缺少类型标注 | 文档没有 `type`/`audience` frontmatter | AI 不知道什么场景加载什么文档 |

### 目标

```
docs/
  README.md                 ← 四象限导航入口 + 角色映射表

  tutorials/                ← 🟢 学习导向：完整步骤，零知识假设
    getting-started.md

  how-to/                   ← 🔵 任务导向：解决具体问题
    configure-review.md
    add-new-agent.md
    customize-hooks.md
    (按需扩展)

  explanation/              ← 🟡 理解导向：为什么这么设计
    architecture.md         ← 已有，合并 guide.md 的架构部分
    state-machine.md        ← 从 guide.md 拆分
    memlog-design.md        ← 从 guide.md 拆分

  reference/                ← 🔴 信息导向：规格清单
    commands.md             ← 从 guide.md 拆分
    config-options.md       ← 从 guide.md 拆分
    agent-index.md          ← 已有
    hooks-registry.md       ← 从 guide.md 拆分
    bmad-optimization-roadmap.md ← 已有

  reports/                  ← 运行时报告（不变）
```

---

## 2. 设计原则

### 2.1 四象限定义

| 象限 | 色标 | 目的 | 读者心态 | 内容特征 |
|------|------|------|---------|---------|
| Tutorials | 🟢 绿 | 学习 | "我想学会" | 完整步骤，每一步解释 |
| How-To | 🔵 蓝 | 解决 | "我要做 X" | 聚焦单一任务，直接可操作 |
| Explanation | 🟡 黄 | 理解 | "为什么这样" | 背景、权衡、设计决策 |
| Reference | 🔴 红 | 查询 | "X 的参数是什么" | 精确、完整、可搜索 |

### 2.2 每个文档强制 frontmatter

```markdown
---
type: tutorial | how-to | explanation | reference
audience: new-user | regular-user | plugin-developer | maintainer
related:
  - reference/commands.md
---
```

---

## 3. 拆分方案

### 3.1 从 `guide.md` 拆分

`guide.md`（当前 ~600 行）按以下规则拆出：

| 源章节 | 目标文件 | 理由 |
|--------|---------|------|
| 1.1 命令详解（7 个子命令） | `reference/commands.md` | AI 和用户都需要快速查命令 |
| 1.2 配置系统 | `reference/config-options.md` | 配置项清单，精确查询 |
| 1.3 测试 | `reference/testing.md` | 测试命令和参数 |
| 1.4 安装目录结构 | `tutorials/getting-started.md`（合并） | 新用户第一步 |
| 2.1 架构总览 | `explanation/architecture.md`（合并已有） | 架构解释 |
| 2.2 状态机 | `explanation/state-machine.md` | 状态机设计原理 |
| 2.3 Memlog 事件源 | `explanation/memlog-design.md` | 事件源设计原理 |
| 2.4 引擎 CLI | `reference/commands.md`（合并） | 命令参考 |
| 2.5 审查门控 | `explanation/architecture.md`（整合） | 门控是架构的一部分 |
| 2.6 Agent 体系 | `reference/agent-index.md`（扩充已有） | Agent 清单 |
| 2.7 钩子系统 | `reference/hooks-registry.md` | Hook 注册表参考 |

拆分后 `guide.md` 标记 deprecated，保留 2 个版本后删除。

### 3.2 新建 `tutorials/getting-started.md`

内容来自 `README.md` 中的快速开始 + `guide.md` 的安装目录结构 + 现状。包含：

```markdown
---
type: tutorial
audience: new-user
---

# 5 分钟上手 animus

1. 安装 animus 插件
2. 在目标项目运行 /animus-init
3. 查看 features.json 了解任务
4. 运行 /animus-dev 开始第一个开发任务
5. 运行 /animus-status 查看进度
```

### 3.3 新建 `how-to/` 目录

初始内容（从已有文档和 FAQ 提炼）：

| 文件 | 内容来源 | 解决什么问题 |
|------|---------|------------|
| `how-to/configure-review.md` | 从 guide.md 审查门控 + 配置系统提取 | "我想调整代码审查的严格程度" |
| `how-to/add-new-agent.md` | 从 agent-index.md + architecture.md 提取 | "我想为某种语言新增 Agent" |
| `how-to/customize-hooks.md` | 从 guide.md 钩子系统提取 | "我想添加一个自定义钩子" |

### 3.4 更新入口导航

在 `docs/README.md` 中放角色→目标→路径映射表：

```markdown
# Animus 文档

| 你的角色 | 你想做什么 | 去哪看 |
|---------|-----------|--------|
| 🆕 新用户 | 第一次使用，快速上手 | `tutorials/getting-started.md` |
| 🔧 日常用户 | 查某个命令的用法 | `reference/commands.md` |
| ⚙️ 项目 Lead | 调整配置/审查规则 | `how-to/configure-review.md` |
| 🏗️ 插件开发者 | 新增 Agent 或语言支持 | `how-to/add-new-agent.md` |
| 🧠 好奇者 | 理解设计原理 | `explanation/architecture.md` |
| 📋 维护者 | 查看路线图和规划 | `reference/bmad-optimization-roadmap.md` |
```

---

## 4. 实施步骤

| # | 内容 | 涉及文件 | 工作量 |
|---|------|---------|--------|
| 1 | 新建目录结构：`tutorials/`、`how-to/`、`explanation/`（已有）、`reference/`（现有文件迁入） | 目录创建 | 极小 |
| 2 | 从 `guide.md` 提取 1.1 命令详解 → `reference/commands.md`，补充命令行表格 | `guide.md` → `reference/commands.md` | 中 |
| 3 | 从 `guide.md` 提取 1.2 配置系统 → `reference/config-options.md`，补充所有配置项 | `guide.md` → `reference/config-options.md` | 小 |
| 4 | 从 `guide.md` 提取 1.3 测试 → `reference/testing.md` | `guide.md` → `reference/testing.md` | 小 |
| 5 | 从 `guide.md` 提取 2.2 状态机 → `explanation/state-machine.md`，与已有 architecture.md 去重 | `guide.md` + `architecture.md` → `explanation/state-machine.md` | 小 |
| 6 | 从 `guide.md` 提取 2.3 Memlog → `explanation/memlog-design.md` | `guide.md` → `explanation/memlog-design.md` | 小 |
| 7 | 从 `guide.md` 提取 2.7 钩子 + 2.4 引擎CLI → `reference/hooks-registry.md` | `guide.md` → `reference/hooks-registry.md` | 小 |
| 8 | 合并 `guide.md` 2.5 审查门控 + 2.6 Agent 体系 → 已有 `architecture.md` 和 `agent-index.md` | `guide.md` + `architecture.md` + `agent-index.md` | 小 |
| 9 | 新建 `tutorials/getting-started.md` | 从 README + guide.md 1.4 提取 | 小 |
| 10 | 新建 `how-to/configure-review.md`、`how-to/add-new-agent.md`、`how-to/customize-hooks.md` | 从现有文档提炼 | 中 |
| 11 | 新建 `docs/README.md` 四象限导航入口 | 新建 | 极小 |
| 12 | 所有文件加 `type` + `audience` frontmatter | 全部 docs/ 文件 | 小 |
| 13 | `guide.md` 顶部加 deprecated 标注，2 个版本后清理 | `guide.md` | 极小 |

---

## 5. 集成方案

### 5.1 CLAUDE.md 指引

在 `CLAUDE.md` 中更新文档路径：

```markdown
## 文档指南

- 新用户从 `docs/tutorials/getting-started.md` 开始
- 命令参考查 `docs/reference/commands.md`
- 配置项查 `docs/reference/config-options.md`
- 架构设计看 `docs/explanation/architecture.md`
```

### 5.2 AI 文档加载策略

AI 在回答问题时可根据 frontmatter 的 `type` 决定加载策略：

| 用户问题 | 应加载的象限 |
|---------|------------|
| "怎么开始？" | tutorials/ |
| "怎么配置 X？" | how-to/ |
| "为什么这样设计？" | explanation/ |
| "X 命令的参数？" | reference/ |

---

## 6. 与现有文档的映射

```
迁移前                                 迁移后
─────────                             ─────────
docs/
  guide.md                              reference/
    1.1 命令详解                 →         commands.md
    1.2 配置系统                 →         config-options.md
    1.3 测试                     →         testing.md
    1.4 安装目录结构             →   tutorials/getting-started.md
    2.1 架构总览                 →   explanation/architecture.md（合并）
    2.2 状态机                   →   explanation/state-machine.md
    2.3 Memlog                   →   explanation/memlog-design.md
    2.4 引擎 CLI                 →   reference/commands.md（合并）
    2.5 审查门控                 →   explanation/architecture.md（合并）
    2.6 Agent 体系               →   reference/agent-index.md（扩充）
    2.7 钩子系统                 →   reference/hooks-registry.md
  
  architecture.md                 →   explanation/architecture.md（不变）
  agent-index.md                  →   reference/agent-index.md（扩充）
  bmad-optimization-roadmap.md    →   reference/bmad-optimization-roadmap.md（不变）
```

---

## 7. 工作量估算

| 阶段 | 内容 | 预估 |
|------|------|------|
| 拆分 guide.md 命令/配置部分 | 复制 + 整理 | ~2h |
| 拆分 guide.md 底层机制部分 | 复制 + 整理 + 去重 | ~2h |
| 新建 getting-started.md | 提炼现有内容 | ~1h |
| 新建 how-to 文件（3 个） | 从 FAQ 和 issue 提炼 | ~2h |
| 入口导航 docs/README.md | 编写 | ~0.5h |
| 加 frontmatter | 每个文件 1 行 | ~0.5h |
| guide.md deprecated 标注 | 加一行 | ~0.1h |

**总工作量：** 小（约 2 天）

---

## 8. 验收标准

| # | 验收条件 | 验证方法 |
|---|---------|---------|
| 1 | `guide.md` 内容已全部拆到对应四象限文件中 | 对比拆分清单，逐条检查 |
| 2 | 每个文件有 `type` + `audience` frontmatter | `grep -r "^type:" docs/ ` |
| 3 | `docs/README.md` 导航表覆盖所有角色 → 目标路径 | 手动检查每行链接可访问 |
| 4 | `tutorials/getting-started.md` 可让新用户 5 分钟内完成首次操作 | 找一人按步骤走一遍 |
| 5 | `reference/commands.md` 覆盖所有 7 个斜杠命令 | 与 plugin.json 对比 |
| 6 | `reference/config-options.md` 覆盖所有配置段 | 与 config_loader.py 的键对比 |
| 7 | `guide.md` 顶部有 deprecated 标注 | 手动检查 |
| 8 | `CLAUDE.md` 中更新了文档路径指引 | 手动检查 |
