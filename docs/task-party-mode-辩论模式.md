# 优化任务：Party Mode 辩论模式（独立 Skill）

> 对应路线图：Phase 2 — 能力增强
> 独立 skill，可被 `/animus-dev --full` 和 `/animus-review` 自动调用

---

## 一、更改原因

### 1.1 当前问题

- 架构评审单 agent 视角不够全面，缺少多方意见碰撞
- 审查遇到 high 级争议时没有升级讨论机制
- 关键决策只有一人观点，容易遗漏盲点
- 辩论过程不记录，决策追溯困难

### 1.2 解决后的效果

- 多 agent 从不同角度碰撞观点，暴露设计盲点
- 共识自动写入 spec.constraints/risks，分歧存独立报告
- 全量辩论日志记入 memlog，可追溯
- 预装 2 个模板，一键启用

---

## 二、更改方案

### 2.1 定位

独立 skill（`skills/party-mode/`），不内嵌于任何命令。被以下方式触发：

| 触发方式 | 场景 | 说明 |
|---------|------|------|
| 自动 | `/animus-dev --full` 方案评审阶段 | 架构评审团模板 |
| 自动 | `/animus-review` 发现 high 级争议 | 代码审查团模板 |
| 手动 | `/animus-party [--template ...] [--mode ...]` | 独立入口 |

自动触发前通过 `config.toml` 的 `ask_before_start` 决定是否询问用户。`autonomous = true` 时全权决策。

### 2.2 4 种运行模式

| 模式 | 说明 | 适用场景 | token 消耗 |
|------|------|---------|-----------|
| `session` | 一个大脑扮演所有角色 | 快速评审 | 最低 |
| `subagent` | 每个角色独立 spawn 子 agent | 正式评审 | 高（效果最好） |
| `auto` | 必要时混入真实 agent | 平衡模式 | 中 |
| `agent-team` | 持久团队（Claude Code 限定） | 跨会话协作 | 中 |

默认模式：`subagent`（通过 `config.toml[party_mode].default_mode` 配置）

### 2.3 模板 A：架构评审团（5 人）

适用于 `/animus-dev --full` 的方案评审阶段。

| Icon | 角色 | 对应现有 Agent | Persona |
|------|------|---------------|---------|
| 🏗️ | 架构师 | `qt/architect` 等 | 你是方案的提出者和捍卫者。你从整体架构一致性的角度出发，清楚每个 trade-off。当别人质疑时，你解释为什么在现有约束下这是最合理的方案。你不会死守方案——如果发现真正的缺陷，你会承认并调整。 |
| 🔍 | 审查官 | `universal/code-reviewer` | 你的任务是给方案「挑刺」。你假设每个方案都有盲点。你关注：异常路径、回滚策略、6 个月后是否还能理解。你不接受「一直这样做」作为理由。 |
| 🧪 | 测试官 | `universal/test-engineer` | 你从「怎么测」的角度反向验证。如果一个设计没法测，那就是有问题的。你关注：单元测试覆盖、集成测试点、边界条件构造、性能指标验证。 |
| 🛠️ | 构建师 | `universal/build-doctor` | 你关注方案从合并到用户用上的全路径。你关注：构建时间、CI 步骤、依赖引入风险、版本兼容性、回滚复杂度。你的核心问题：「这个方案上线和回滚分别需要几步？」 |
| 📋 | 规划师 | `universal/feature-planner` | 你把方案拆成可执行的任务。你关注：第一步做什么最能验证可行性、哪些可并行、哪些风险项需要先做。 |

### 2.4 模板 B：代码审查团（4 人）

适用于审查出现 high 级争议时。

| Icon | 角色 | 对应 Agent | Persona |
|------|------|-----------|---------|
| 🔍 | 审查官 | `code-reviewer` | 你负责找出代码中的正确性问题。你假设每段代码都有 bug。你关注：空指针、类型错误、资源泄漏、竞态条件、安全漏洞。 |
| 🌶️ | 边界猎手 | 新建 `edge-case-hunter` | 你遍历每条执行路径，找「正常情况不会发生但发生了就崩了」的场景。你关注：空集合、零值、负数、并发写入、重试风暴、超时、OOM、Unicode 特殊字符。 |
| ✅ | 验收审计官 | 新建 `acceptance-auditor` | 你对照 features.json 的 spec.success，逐条确认代码是否满足验收条件。你产出 PASS/FAIL 逐条判定。 |
| ✂️ | 精简审查官 | 新建 `ponytail-reviewer` | 你专门找「不必要的代码」。你关注：可有可无的抽象层、提前做的扩展点、重复的工具函数。你的原则：能删则删，能简则简。 |

### 2.5 辩论流程

```
触发（自动/手动）
  → 用户确认是否启动辩论
  → 选择模板（或使用默认）
  → 选择运行模式（或使用默认）
  → 4 阶段辩论：
      ① 方案陈述——每个角色从自己的角度发表意见
      ② 质疑交锋——角色间互相提问和反驳
      ③ 共识/分歧记录——标记一致和不一致的点
      ④ 合成输出——共识写入 spec，分歧存报告
  → 全量日志写入 memlog（事件类型：辩论）
  → 共识自动写入 features.json 对应任务的 spec.constraints 和 spec.risks
  → 分歧存独立辩论报告（debate-report.md）
```

### 2.6 持久记忆

辩论全量日志写入 memlog，事件类型为 `辩论`：

```
.claude/animus/memlog/
└── 2026-07-04-1400-辩论-架构评审-T003.md
```

内容包含：模板名称、参与角色列表、每个角色的观点摘要、共识点列表、分歧点列表、最终裁决。

### 2.7 配置项（config.toml）

```toml
[party_mode]
default_mode = "subagent"         # session / subagent / auto / agent-team
default_party = "arch-review"     # arch-review / code-review
auto_trigger = ["dev-full", "review-controversial"]
ask_before_start = true
max_rounds = 3
memory_enabled = true

# 自定义角色
[[party_mode.custom_members]]
code = "ui-reviewer"
name = "UI 审查官"
icon = "\U0001F3A8"
title = "前端可用性审查"
persona = "关注界面可用性和用户体验……"

# 自定义模板
[[party_mode.custom_groups]]
id = "my-team"
name = "我的团队"
members = ["architect", "reviewer", "ui-reviewer"]
scene = "针对 UI 改动进行评审……"
```

### 2.8 改动文件

| 文件 | 改动 |
|------|------|
| 新建 `skills/party-mode/SKILL.md` | 辩论流程编排入口 |
| 新建 `skills/party-mode/customize.toml` | 模板定义、角色配置 |
| 新建 `skills/party-mode/templates/arch-review.json` | 架构评审团模板 |
| 新建 `skills/party-mode/templates/code-review.json` | 代码审查团模板 |
| 新建 `commands/animus-party.md` | 手动入口 |
| 修改 `commands/animus-dev.md` | full-path 自动触发 + 询问确认 |
| 修改 `commands/animus-review.md` | high 争议时自动触发 |
| `plugin.json` | 注册新命令 |
| `.claude/animus/config.toml` | `[party_mode]` 配置段 |
| `scripts/engine/cmd_transition.py` | 辩论结果自动写入 spec |

---

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 辩论模式 token 消耗较大（多 agent 对话），但仅在 full-path 或 high 争议时触发 |
| 兼容性 | `/animus-dev` 和 `/animus-review` 接口不变，辩论为可选附加流程 |
| 降级 | 辩论失败/超时 → 降级为常规单 agent 审查，不阻塞主流程 |
