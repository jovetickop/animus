# 优化任务 ①：命名 Agent 角色系统

> 对应路线图：Phase 1 — 快速见效 / P0

---

## 一、更改原因

### 1.1 当前问题

Animus 现有 22 个 agent，全部按功能路径命名：

```
agents/qt/architect.md
agents/node/test-engineer.md
agents/universal/code-reviewer.md
```

用户看到的是"一个文件路径"，不是"一个协作者"。具体痛点：

- **认知成本高：** 用户不知道 `architect.md` 和 `feature-planner.md` 的区别，也不知道该叫谁做什么
- **缺乏人格化：** agent 回复时没有身份标识，用户感受不到"谁在帮我"，降低协作信任
- **入口分散：** 没有统一的"谁负责什么"一览表

### 1.2 解决后的效果

- 用户看到"架构师 (Qt)"立刻知道找谁
- agent 回复时自报身份：`我是架构师 (Qt)，正在审查你的类设计...`
- agent-index 一目了然，新用户 10 秒找到对应角色

---

## 二、更改方案

### 2.1 命名风格

格式：`显示名 (缩写)` — 副标题

每个 agent frontmatter 包含 3 个字段：

```yaml
---
name: 架构师 (Qt)
title: Qt 类设计与架构决策
team: qt
---
```

| 字段 | 示例 | 用途 |
|------|------|------|
| `name` | `架构师 (Qt)` | 显示名，agent 自报身份用 |
| `title` | `Qt 类设计与架构决策` | 副标题，说明角色职责 |
| `team` | `qt` / `universal` | 分组索引，用于 agent-index 按团队展示 |

### 2.2 全文命名映射

#### base/（2 个核心模板）— team: base

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `task-implementer-core.md` | 实现者 (Core) | 多语言通用实现模板 | base |
| `test-engineer-core.md` | 测试官 (Core) | 多语言通用测试模板 | base |

#### universal/（5 个跨语言）— team: universal

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `feature-planner.md` | 规划师 (Plan) | 任务拆解与进度编排 | universal |
| `task-implementer.md` | 实现者 (Impl) | 增量编码与构建修复 | universal |
| `test-engineer.md` | 测试官 (Test) | 测试方案设计与验证 | universal |
| `build-doctor.md` | 构建师 (Build) | 构建问题诊断与修复 | universal |
| `code-reviewer.md` | 审查官 (Review) | 代码质量门控审查 | universal |

#### qt/（4 个 Qt/C++）— team: qt

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `architect.md` | 架构师 (Qt) | Qt 类设计与架构决策 | qt |
| `task-implementer.md` | 实现者 (Qt) | Qt 增量编码实现 | qt |
| `test-engineer.md` | 测试官 (Qt) | Qt 测试验证 | qt |
| `ui-reviewer.md` | UI 审查官 (Qt) | Qt 界面可用性审查 | qt |

#### node/（3 个）— team: node

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `architect.md` | 架构师 (Node) | Node/Web 架构设计与选型 | node |
| `test-engineer.md` | 测试官 (Node) | Node 测试方案 | node |
| `ui-reviewer.md` | UI 审查官 (Web) | 前端界面可用性审查 | node |

#### python/（2 个）— team: python

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `architect.md` | 架构师 (Py) | Python 架构设计与选型 | python |
| `test-engineer.md` | 测试官 (Py) | Python 测试方案 | python |

#### rust/（2 个）— team: rust

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `architect.md` | 架构师 (Rust) | Rust 架构设计与选型 | rust |
| `test-engineer.md` | 测试官 (Rust) | Rust 测试方案 | rust |

#### go/（2 个）— team: go

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `architect.md` | 架构师 (Go) | Go 架构设计与选型 | go |
| `test-engineer.md` | 测试官 (Go) | Go 测试方案 | go |

#### cpp-cmake/（1 个）— team: cpp-cmake

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `architect.md` | 架构师 (Cpp) | C++/CMake 构建方案设计 | cpp-cmake |

#### frontend/（1 个）— team: frontend

| 文件 | 显示名 | 副标题 | team |
|------|--------|--------|------|
| `feature-planner-frontend.md` | 规划师 (FE) | 前端任务规划补充指南 | frontend |

### 2.3 改动内容

#### 2.3.1 每个 agent 文件的 frontmatter

当前有的 agent 文件有 frontmatter，有的没有。统一加 2 个字段：

```yaml
---
name: 架构师 (Qt)
title: Qt 类设计与架构决策
---
```

**改动文件：** 所有 21 个 agent 文件（不含 README.md）
**改动量：** 每个文件增加 2-3 行 frontmatter

#### 2.3.2 agent-index 文档

`docs/agent-index.md` 当前有表格索引，在显示列追加显示名。

| 修改内容 | 位置 |
|---------|------|
| 表格加"显示名"列 | `docs/agent-index.md` |
| 按目录分组加副标题描述 | `docs/agent-index.md` |

#### 2.3.3 plugin.json description（可选）

`plugin.json` 的 description 字段提及命名 agent，增加可信度：

```
"description": "状态机驱动的 AI 编码工作流引擎。包含 6 大角色：规划师(Plan)、架构师(Qt/Rust/Go/...)、实现者、测试官、审查官(Review)、构建师(Build)。..."
```

#### 2.3.4 agent 回复时自报身份

理论上每个 agent 的 system prompt 头部应加入一句话：

```
你在回复时先自报身份："我是 {name}（{title}），正在处理你的请求。"
```

但这需要改动 21 个 agent 文件正文，量较大。**暂缓**，先只做 frontmatter，后续再决定是否加说话人格。

### 2.4 不改动的部分

- agent 文件正文内容（function body、system prompt 逻辑）— 不变
- 文件路径和文件名 — 不变（避免关联引用断裂）
- agent 行为逻辑 — 不变

### 2.5 改动文件清单

```
agents/base/task-implementer-core.md        + frontmatter
agents/base/test-engineer-core.md           + frontmatter
agents/universal/feature-planner.md          + frontmatter
agents/universal/task-implementer.md         + frontmatter
agents/universal/test-engineer.md            + frontmatter
agents/universal/build-doctor.md             + frontmatter
agents/universal/code-reviewer.md            + frontmatter
agents/qt/architect.md                       + frontmatter
agents/qt/task-implementer.md                + frontmatter
agents/qt/test-engineer.md                   + frontmatter
agents/qt/ui-reviewer.md                     + frontmatter
agents/node/architect.md                     + frontmatter
agents/node/test-engineer.md                 + frontmatter
agents/node/ui-reviewer.md                   + frontmatter
agents/python/architect.md                   + frontmatter
agents/python/test-engineer.md               + frontmatter
agents/rust/architect.md                     + frontmatter
agents/rust/test-engineer.md                 + frontmatter
agents/go/architect.md                       + frontmatter
agents/go/test-engineer.md                   + frontmatter
agents/cpp-cmake/architect.md                + frontmatter
agents/frontend/feature-planner-frontend.md  + frontmatter
docs/agent-index.md                          + 显示名 + team 列
.claude-plugin/plugin.json                   + description 更新
```

共 **23 个文件**，每个文件修改量 3-5 行。

---

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 无影响——只加 frontmatter 元数据，不改变加载和执行逻辑 |
| 兼容性 | 完全向后兼容——旧引用路径不变，缺失 frontmatter 字段的 agent 自动降级为无 name 状态 |
| 降级 | 某个 agent 没加字段时，系统正常运转，仅不显示 name/title/team |

## 四、验证方法

1. 读取任意改过的 agent 文件，确认 frontmatter `name`、`title`、`team` 字段正确
2. 确认核心 agent 的 `persona` 字段存在且内容正确
3. 确认文件名未变，其他文件对 agent 的引用路径不受影响
4. 读 `docs/agent-index.md` 确认表格格式正确（含 team 列）
5. 读 `plugin.json` 确认 JSON 格式正确
