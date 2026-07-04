---
type: reference
audience: maintainer
---

# BMAD 启发优化路线图

> 基于 BMAD Method v6.10.0 特性分析，针对 animus (ty-qt-ai-plugin) 的优化方向与实施路线图。
> 生成日期：2026-07-04

---

## 路线图总览

```
Phase 0 (基础设施)       Phase 1 (核心体验)         Phase 2 (能力增强)         Phase 3 (深度建设)
├── ⑨ 配置系统（两层）     ├── ① 命名 Agent          ├── ④ 工作流地图          ├── ⑩ SPEC 内核
├── ⑥ 引擎脚本化         ├── ② Memlog 持久化       ├── ⑦ 对抗性审查
                        ├── ③ 文档四象限重构 🆕    ├── ⑪ 双模式验证器 🆕
                        ├── ⑫ 编号菜单 🆕         ├── ⑧ 头脑风暴
                        ├── Party Mode
                        └── ⑤ Quick Dev
                                                   └── 多 IDE 适配
```

---

## Phase 0：基础设施（第 1-2 周）—— 必须先做

> **依赖关系：** Phase 0 是 Phase 1-3 的基础依赖。配置体系和 engine CLI 不完成，后续所有模块无法正常工作。

### 0.1 配置系统（两层） [✅ 已完成 2026-07-04]

**现状：** 所有行为硬编码。用户想改审查严格度或添加自定义规则要 fork 插件。

**目标：** `.claude/animus/config.toml` 两层配置（defaults[硬编码] ← config.toml），控制全部行为。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 0.1.1 | 创建 `.claude/animus/config.toml` 默认配置（全配置段） | 新建 `.claude/animus/config.toml` |
| 0.1.2 | 实现 Python `load_config()` 两层覆盖合并 | `scripts/config_loader.py` |
| 0.1.3 | 实现 Python `load_config()` 两层覆盖合并 | `scripts/config_loader.py` |
| 0.1.4 | 合并 `project-config.json` 进 config.toml | `.claude/animus/config.toml` |

**配置段：** `[dev]` `[review]` `[gates]` `[ponytail]` `[party_mode]`

**工作量估算：** 中
**预期效果：** 所有后续模块的配置统一入口，无需 fork 插件
`task-09-配置系统（两层）.md`

---

### 0.2 引擎脚本化（animus-engine.py） [✅ 已完成 2026-07-04]

**现状：** 核心逻辑使用 Python 脚本。

**目标：** `scripts/animus-engine.py` 统一 CLI + `scripts/engine/` 子命令模块。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 0.2.1 | 创建 `scripts/animus-engine.py`（argparse 入口） | 新建 |
| 0.2.2 | 创建子命令模块：`cmd_status.py` `cmd_transition.py` `cmd_validate.py` `cmd_archive.py` `cmd_rebuild.py` | 新建 `scripts/engine/*.py` |
| 0.2.3 | 现有 `.md` 命令和 hooks 改为调 engine CLI | 所有 command 和 hook 文件 |

**子命令：** status / transition / validate / archive / rebuild

**工作量估算：** 中高
**预期效果：** 引擎独立可测，未来可移植到其他 IDE
`task-06-多IDE引擎抽离.md`

---

### Phase 1：核心体验（第 3-5 周）

### 1.1 命名 Agent 角色系统 [✅ 已完成 2026-07-04]

**现状：** 22 个 agent 按功能路径命名，用户看到的是文件路径不是协作者。

**目标：** 所有 agent 加 frontmatter 3 字段（name/title/team），5 个核心 agent 加完整 persona。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 1.1.1 | 所有 22 个 agent frontmatter 加 `name`、`title`、`team` | 所有 agent 文件 |
| 1.1.2 | 5 个核心 agent（规划师/审查官/架构师/实现者/构建师）加 `persona` 字段 | 核心 agent 文件 |
| 1.1.3 | 更新 `docs/agent-index.md` 加显示名和 team 列 | `docs/agent-index.md` |
| 1.1.4 | 更新 `plugin.json` description 提及命名 agent | `.claude-plugin/plugin.json` |

**工作量估算：** 22 个 agent 文件 × 5 行修改 + 5 个 persona × 50 字 ≈ 中
**预期效果：** 用户感知从工具集 → 团队协作者

**命名映射（摘要）：** `task-01-命名Agent.md`

---

### 1.2 Memlog 模式状态持久化 [✅ 已完成 2026-07-04]

**现状：** memlog 框架已就绪：`scripts/memlog.py`（事件写入）、`cmd_rebuild.py`（重建）

**目标：** 引入 append-only memlog 作为单一事件源，状态文件从 memlog 派生（派生可删除重建，memlog 永不删除）。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 1.2.1 | 定义 memlog 格式：`YYYY-MM-DD-HHmm-{event-type}.md`，append-only | 新建 `.claude/animus/memlog/` 目录 |
| 1.2.2 | 事件类型定义：「创建任务」「状态变更」「决策」「交接」「归档」「辩论」 | `docs/architecture.md` 更新 |
| 1.2.3 | `scripts/engine/cmd_rebuild.py` 从 memlog 重建 features.json | `scripts/engine/cmd_rebuild.py` |
| 1.2.4 | PreCompact hook 已集成 memlog 事件追加 | `hooks/scripts/pre-compact.py` |
| 1.2.5 | 删除 `/animus-handoff` 和 `/animus-continue`（已移除，memlog 自动接管） | 删除 `commands/animus-handoff.md` `commands/animus-continue.md` |
| 1.2.6 | `scripts/engine/cmd_rebuild.py` 恢复脚本 | `scripts/engine/cmd_rebuild.py` |

**文件名示例：** `2026-07-04-1001-创建任务-T003-添加PDF导出功能.md`（中文文件名和内容）

**事件类型：** 创建任务 / 状态变更 / 决策 / 交接 / 归档 / 辩论

`task-02-Memlog持久化.md`

**工作量估算：** 4 个脚本修改 + 2 个目录结构 + 1 个新脚本 ≈ 中
**预期效果：** 消除多文件同步不一致，灾难恢复能力从"可能丢"变"不丢"

---

### 1.3 文档四象限重组（Docs Quadrant Restructure） [🆕 方案已定]

**现状：** `docs/guide.md` 混合用户指南和底层机制两类内容（~600 行），新用户找不到入口，AI 无法按类型加载。

**目标：** 按 Tutorials / How-To / Explanation / Reference 四象限重组文档，每个文件加 `type` + `audience` frontmatter，入口放角色→目标→路径导航表。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 1.3.1 | 新建目录结构 `tutorials/` `how-to/` `reference/`（explanation/ 已有） | 目录创建 |
| 1.3.2 | 从 guide.md 拆分命令详解 → `reference/commands.md` | `guide.md` → `reference/commands.md` |
| 1.3.3 | 从 guide.md 拆分配置系统 → `reference/config-options.md` | `guide.md` → `reference/config-options.md` |
| 1.3.4 | 从 guide.md 拆分测试 → `reference/testing.md` | `guide.md` → `reference/testing.md` |
| 1.3.5 | 从 guide.md 拆分状态机/Memlog/钩子 → `explanation/` + `reference/` | `guide.md` → 各目标文件 |
| 1.3.6 | 新建 `tutorials/getting-started.md` + `how-to/` 初始 3 文件 | 新建 |
| 1.3.7 | 新建 `docs/README.md` 四象限导航入口 | 新建 |
| 1.3.8 | 所有文档加 `type` + `audience` frontmatter | 全部 docs/ 文件 |
| 1.3.9 | guide.md 顶部加 deprecated 标注 | `guide.md` |

**工作量估算：** 小（约 2 天）
**预期效果：** 新用户 5 分钟找到入口，AI 按类型精准加载文档
`docs/task-docs-quadrant.md`

---

### 1.4 Agent 编号菜单 [🆕 方案已定]

**现状：** Agent 激活后无菜单引导。用户不知道 Agent 能做什么，AI 猜方向可能错，浪费多轮对话。

**目标：** 为 8 个核心 Agent 添加数字编号菜单（1 2 3 4），激活后展示可选路径。意图明确时跳过菜单直接执行。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 1.4.1 | 实现者加菜单（修复Bug/新功能/重构/快速开发） | `agents/universal/task-implementer.md` |
| 1.4.2 | 规划师加菜单（差距分析/任务拆分/更新术语/完整流程） | `agents/universal/feature-planner.md` |
| 1.4.3 | 审查官加菜单（全面审查/安全/性能/仅测试） | `agents/universal/code-reviewer.md` |
| 1.4.4 | 测试官加菜单（设计方案/生成测试/审查测试） | `agents/universal/test-engineer.md` |
| 1.4.5 | 构建师加菜单（定位错误/依赖诊断/配置修复/完整诊断） | `agents/universal/build-doctor.md` |
| 1.4.6 | Qt 层同步（实现者加 UI 调试项、测试官、UI 审查官） | `agents/qt/*.md` |
| 1.4.7 | 其他语言（python/node/rust/go）测试官同步 | `agents/*/test-engineer.md` |
| 1.4.8 | 更新 agent-index.md 说明菜单功能 | `docs/agent-index.md` |

**工作量估算：** 极小（约 1 天），纯 Markdown
**预期效果：** 用户激活 Agent 后立即知道能做什么，输入数字即可，减少方向猜错
`docs/task-agent-menus.md`

---

## Phase 2：能力增强（第 5-8 周）

### 2.1 工作流地图 / 智能导航 [✅ 已完成 2026-07-04]

**现状：** 用户只能自己判断"下一步做什么"。缺乏类似 BMAD `bmad-help` 的上下文感知推荐。

**目标：** `/animus-status` 集成推荐引擎，显示"基于当前状态，建议下一步"。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 2.1.1 | 在 `cmd_status.py` 中内嵌 WORKFLOW_GRAPH Python dict | `scripts/engine/cmd_status.py` |
| 2.1.2 | `cmd_status.py` 根据 DAG 和当前 features.json 计算推荐下一步 | `scripts/engine/cmd_status.py` |
| 2.1.3 | `/animus-status` 输出追加推荐块 | `commands/animus-status.md` |
| 2.1.4 | `/animus-status` 输出底部追加推荐区块 | `commands/animus-status.md` |

**DAG 示例：**

```yaml
commands:
  animus-init:
    pre: []
    post: [".claude/animus/features.json 存在"]
    next: [animus-dev]

  animus-dev:
    pre: [".claude/animus/features.json 存在"]
    post: ["features.json 有 in_progress 任务"]
    next: [animus-review]

  animus-review:
    pre: ["features.json 有 passed 任务"]
    post: ["审查报告已生成"]
    next: [animus-archive]

  animus-archive:
    pre: ["所有任务已完成"]
    post: ["features.json 已清空"]
    next: [animus-dev]
```

**工作量估算：** 1 个脚本修改 + 1 个命令修改 ≈ 小
**预期效果：** 用户不再停滞，"做完 A 不知道 B" 的场景消除

---

### 2.2 Quick Dev 快速通道 [✅ 已完成 2026-07-04]

**现状：** 即使 5 行代码的 bug fix，也要走完 Grilling 7 问 + feature-planner，太重。

**目标：** `/animus-dev` 命令：四路路由（debug/fast/light/full）。AI 自动选路 + 用户确认，`autonomous = true` 时跳过确认。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 2.2.1 | 新建 `/animus-dev` 命令，五路路由（含 debug-path）| 新建 `commands/animus-dev.md` |
| 2.2.2 | 智能路由逻辑 + 路径确认机制 | 同上 |
| 2.2.3 | 删除 `/animus-plan`（不留 deprecated） | 删除 `commands/animus-plan.md` |
| 2.2.4 | 配合 write-gate hook 硬拦截 | `hooks/scripts/write-gate.py`、`.sh` |

**路由决策树：**

```
用户输入 → 检测意图类型
  ├── bug 报告/异常 → debug-path（3 问调试专用）
  ├── 1-2 文件 / 小改动 → fast-path（1 句确认）
  ├── 3-10 文件 / 新增 → light-path（3 问）
  └── 跨模块 / 架构改动 → full-path（7 问 + 可选脑暴 + Party Mode）
```

**工作量估算：** 1 个新命令 + 1 个脚本修改 ≈ 小
**预期效果：** 小改动耗时从 20+ 轮对话缩减至 3-5 轮

---

### 2.3 对抗性审查系统 [✅ 已完成 2026-07-04]

**现状：** `/animus-review` 单 agent 审查，缺少盲点覆盖。

**目标：** 4 agent 平行审查 + 3 轮循环回退 + 严格模式超时降级。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 2.3.1 | 新增 3 个审查 agent：`edge-case-hunter`、`acceptance-auditor`、`ponytail-reviewer` | 新建 3 个 agent 文件 |
| 2.3.2 | 修改 `/animus-review` 并行调用 4 个审查 agent + 3 轮循环回退 + 超时降级 | `commands/animus-review.md` |
| 2.3.3 | 结果聚合：4 份报告汇总 + 门控裁决（high 阻塞/medium 确认/low 通过） | 同上 |
| 2.3.4 | features.json 门控逻辑改为"四审无 high" + 循环回退计数 | `scripts/engine/cmd_validate.py` |

**审查维度分配：**

| Agent | 角色 | 重点检查项 |
|-------|------|-----------|
| code-reviewer | 审查官 | 正确性 bug、安全、竞态 |
| edge-case-hunter | 边界猎手 | 空值、溢出、并发、资源泄露 |
| acceptance-auditor | 验收审计官 | 逐条核对 features.json spec.success |
| ponytail-reviewer | 精简审查官 | 过度工程、可删减代码 |

**工作量估算：** 3 个新 agent + 1 个命令修改 + 1 个脚本修改 ≈ 中高
**预期效果：** 漏过缺陷概率从单审级别降到三方互验级别

---

### 2.4 双模式验证器（Dual-Mode Plugin Validator） [🆕 方案已定]

**现状：** 只有 `cmd_validate.py` 校验目标工程的 features.json，不触及插件自身的完整性。Agent 缺 frontmatter、Hook 引用失效、索引文档遗漏——全部靠人工发现。

**目标：** 引入双模式验证器——确定性模式（`plugin-validator.py`，8 条硬规则 + JSON 输出）自动检测结构问题，语义模式（`plugin-validator-guide.md`，8 条 AI 可读规则）辅助 AI 做质量审查。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 2.4.1 | 新建 `plugin-validator.py`，实现 R1-R5（结构核心规则） | 新建 `scripts/plugin-validator.py` |
| 2.4.2 | 实现 R6-R8（职责重叠检测、孤立文件、配置一致性） | `scripts/plugin-validator.py` |
| 2.4.3 | 实现 --json / --strict / --fix 输出模式 | `scripts/plugin-validator.py` |
| 2.4.4 | 注册到 `animus-engine.py validate --plugin` | `scripts/animus-engine.py` |
| 2.4.5 | 新建 `docs/plugin-validator-guide.md`，撰写 S1-S8 语义规则 | 新建 `docs/plugin-validator-guide.md` |
| 2.4.6 | Hook 集成 + CLAUDE.md 指引 | `hooks/hooks.json`、`CLAUDE.md` |
| 2.4.7 | 测试用例 + fixtures | `tests/test_plugin_validator.py`、`tests/fixtures/` |

**工作量估算：** 中（约 3-5 天）
**预期效果：** 插件修改后自动检查结构完整性，减少"漏了没发现"的问题
`docs/task-plugin-validator.md`

---

### 2.5 多 IDE 适配准备

**现状：** 锁在 Claude Code。BMAD 覆盖 4 个 IDE，同一套 skill 多平台。

**目标：** 核心状态机引擎抽离为独立 Python CLI，IDE 只做 adapter。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 2.5.1 | 抽取状态机核心逻辑为统一 CLI（见 Phase 0 引擎脚本化） | 见 Phase 0 — 此步骤已在 Phase 0 完成 |
| 2.5.2 | 定义引擎子命令接口文档 | `docs/engine-api.md` |
| 2.5.3 | 现有 `.md` 命令全部改为调 `python animus-engine.py <子命令>`（已在 Phase 0 完成） | 所有 command 文件 |
| 2.5.4 | Cursor adapter 参考 BMAD `references/copilot-tools.md` | `docs/multi-ide.md` |

**工作量估算：** 引擎已在 Phase 0 完成，此阶段仅需文档和验证 ≈ 小
**预期效果：** IDE 锁定的风险移除，生态扩展

---

## Phase 3：深度建设（第 9-10 周）

### 3.1 头脑风暴与产品发现 [✅ 已完成]

**现状：** 6 个独立技法文件已从 BMAD 参考改编，集成到 `/animus-dev --full` 的 7 问之前。

**目标：** 集成到 `/animus-dev --full` 的 7 问之前，6 个技法覆盖不同场景。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 3.1.1 | 新建 `skills/brainstorming/` 目录（6 个技法实现） | 新建 `skills/brainstorming/` |
| 3.1.2 | 集成到 `/animus-dev --full` 的 7 问 Grilling 之前 | `commands/animus-dev.md` |
| 3.1.3 | 分析结果自动写入 features.json 的 spec 字段 | `commands/animus-dev.md` |

**工作量估算：** 1 命令 + 1 skill 目录 ≈ 中
**预期效果：** 从"只能执行"到"也能帮用户想"

---

### 3.2 配置系统 — 已提前至 Phase 0

> **已迁移：** 配置系统（两层）已作为基础设施，提前至 Phase 0 完成。
> `task-09-配置系统（两层）.md`

---

### 3.3 SPEC 内核 / 任务质量契约 [✅ 已完成]

**现状：** `features.json` 任务描述格式自由，缺少结构化的 Why / Success Signal。

**目标：** 每个任务强制包含 SPEC 五字段（Why、Capabilities、Constraints、Non-goals、Success）。

**实施步骤：**

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 3.3.1 | 已完成—— spec 5 字段（why/capabilities/constraints/non_goals/success） | `templates/animus/features.json` |
| 3.3.2 | 已完成—— 实现 4 法则校验（why/capabilities/constraints/success） | `scripts/engine/cmd_validate.py` |
| 3.3.3 | 修改 accept-auditor 验证 Spec.Success 是否满足 | `agents/universal/acceptance-auditor.md` |
| 3.3.4 | 在 `domain-lexicon.md` 中维护 Spec 中出现的术语 | `.claude/animus/domain-lexicon.md` |

**工作量估算：** 中
**预期效果：** 任务质量从"写了"升级到"可验证"

---

## Future：长期探索

### F.1 Web Bundles（成本优化）

将 Grilling 阶段打包为独立 web app，跑在 Gemini/ChatGPT 包月订阅上。

**触发条件：** Phase 1-2 全部上线，用户群足够
**估算效益：** LLM 成本降低 90%（从按量到包月）

### F.2 自举（Animus 开发 Animus） [◐ 部分完成]

用 animus 自身的状态机来管理 animus 插件的开发迭代。目前 `.claude/animus/` 已有目录但未实际用于开发。

**触发条件：** 核心功能稳定
**估算效益：** 吃自己的狗粮，所有改进都通过 animus 流程交付

---

## 推荐优先级矩阵

```
Phase 0（第 1-2 周）      Phase 1（第 3-5 周）      Phase 2（第 5-8 周）      Phase 3（第 9-10 周）
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│ ⑨ 配置系统（两层）    │   │ ① 命名 Agent        │   │ ④ 工作流地图        │   │ ⑩ SPEC 内核 [✅]  │
│ ⑥ 引擎脚本化         │   │ ② Memlog 持久化     │   │ ⑦ 对抗性审查        │   │                     │
│                    │   │ ③ 文档四象限 🆕     │   │ ⑪ 双模式验证器 🆕   │   │                     │
│                    │   │ ⑫ 编号菜单 🆕      │   │                     │   │                     │
│                    │   │ Party Mode [✅]      │   │                     │   │                     │
│                    │   │ ⑤ Quick Dev        │   │ ⑧ 头脑风暴          │   │                     │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘
注：⑥ 多 IDE 引擎已在 Phase 0 完成（引擎脚本化），Phase 2 的多 IDE 适配仅为文档和验证
```

---

## 附录：和 BMAD 的协作建议

以上优化不一定全部从零实现。建议策略：

| 能力 | 参考做法 |
|------|---------|
| 命名 Agent personas | 参考 BMAD `module.yaml` agent roster 的 code/name/icon/team/persona 体系 |
| 对抗性审查循环回退 | 参考 BMAD 最多 5 轮回退（Animus 改为 3 轮） |
| Party Mode 模板+模式 | 参考 BMAD `bmad-party-mode` 的 4 种运行模式 + 预装模板 + customize.toml |
| 双模式验证管道 | 参考 BMAD `validate-skills.js` + `skill-validator.md` 模式 — 已形成方案文档 `docs/task-plugin-validator.md` |
| CSV 路由表 | 参考 BMAD `module-help.csv` 的 phase/pre/post 映射 |
| deprecation 体系 | 参考 BMAD `removals.txt` + `aliases` + `deprecated` 字段 |

BMAD Method 是 MIT 开源，可以直接引用其 skill 文件而不必重造轮子。
