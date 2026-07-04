---
type: reference
audience: plugin-developer
---

# Agent 编号菜单系统（Agent Numbered Menus）

> 为最常用的核心 Agent 添加编号选择菜单（1 2 3 4），用户激活 Agent 后一目了然知道它能做什么，输入数字即可选择处理路径。
> 参考 BMAD Method 的 agent menu 系统，改用数字编号替代字母码。

---

## 1. 背景与动机

### 现状

当前 Agent 激活后，用户只能靠自然语言描述需求，AI 自行判断"做什么"。问题：

| 问题 | 表现 | 影响 |
|------|------|------|
| 用户不知道 Agent 能做什么 | 只能试或翻文档 | 新用户困惑，高级用户也觉得慢 |
| AI 可能猜错方向 | "帮我看看这个"→AI 修 bug，但用户想重构 | 浪费 3-5 轮纠正对话 |
| 同 Agent 不同模式无区分 | task-implementer 既修 bug 又做新功能又重构，全凭 AI 猜 | 行为不确定 |

### 目标

在 Agent 激活步骤末尾添加**编号菜单**，用户输入数字或自然语言描述即可选择路径。意图明确时跳过菜单直接执行。

---

## 2. 设计原则

### 2.1 格式规范

```
💻 Amelia (Senior Software Engineer) — 请选择处理方式：

  1. 修复 Bug — 按 Story AC 逐条修复现有功能的缺陷
  2. 实现新功能 — 按 Story 文件执行完整功能开发
  3. 代码重构 — 不改变行为，只改进代码结构与可维护性
  4. 快速开发 — 小改动，跳过 Story 创建，直接编码

输入数字（1-4）或直接说明你的需求。如果需求明确匹配某项，我会自动选择。
```

### 2.2 规则

| 规则 | 说明 |
|------|------|
| **编号** | 用 `1 2 3 4`，不用字母码（更直观，减少记忆负担） |
| **可跳过** | 用户意图明确时（如"修这个 bug"）直接执行，不展示菜单 |
| **可混合** | 用户输入数字或自然语言均可，Agent 统一处理 |
| **一致性** | 所有 Agent 的菜单放在激活步骤的最后 |
| **简洁** | 每项不超过 15 字描述，避免菜单过长 |

### 2.3 菜单位置

菜单放在每个 Agent 的激活步骤末尾，在"问候用户"之后、"开始主流程"之前：

```
现有步骤:
  Step 1-3: 加载配置 → 加载事实 → 问候用户

新增步骤:
  Step 4: 展示菜单 ← 这里插入
    如果用户意图明确匹配某个菜单项 → 直接跳转到对应路径
    如果不明确 → 展示菜单等待用户选择

后续步骤:
  Step 5+: 根据选择的路径执行
```

---

## 3. 各 Agent 菜单设计

### 3.1 实现者 `agents/universal/task-implementer.md`

```
💻 实现者 (Impl) — 请选择处理方式：

  1. 修复 Bug — 按 Story AC 逐条修复缺陷，先加回归测试再修代码
  2. 实现新功能 — 按 Story/PRD 执行完整功能开发
  3. 代码重构 — 不改变行为，改进结构与可维护性
  4. 快速开发 — 小改动（1-3 文件），跳过 Story 创建步骤
```

用户说"修这个崩溃 bug"→ 匹配路径 1，直接执行，不展示菜单。
用户说"帮我实现用户登录功能"→ 匹配路径 2。
用户说"帮我看看这段代码"→ 不明确，展示菜单。

### 3.2 规划师 `agents/universal/feature-planner.md`

```
📋 规划师 (Plan) — 请选择：

  1. 差距分析 — 对比 PRD/方案与当前 features.json，输出差距清单
  2. 任务拆分 — 将需求拆解为小粒度任务，写入 features.json
  3. 更新术语 — 提取领域术语，更新 domain-lexicon.md
  4. 完整流程 — 差距分析 → 用户确认 → 任务拆分 → 更新术语
```

### 3.3 审查官 `agents/universal/code-reviewer.md`

```
🔍 审查官 (Review) — 请选择审查重点：

  1. 全面审查 — 代码质量 + 测试覆盖 + 安全性 + 变更影响
  2. 安全专项 — 硬编码密钥、用户输入校验、信息泄露、注入风险
  3. 性能专项 — 资源泄漏、不必要的分配、并发瓶颈
  4. 仅测试覆盖 — 只检查测试是否充分，不审查代码风格
```

### 3.4 测试官 `agents/universal/test-engineer.md`

```
🧪 测试官 (Test) — 请选择：

  1. 设计测试方案 — 根据验收标准设计测试矩阵与策略
  2. 生成测试代码 — 为指定功能生成可运行的测试代码
  3. 审查现有测试 — 审查已有测试的覆盖率与质量
```

### 3.5 构建师 `agents/universal/build-doctor.md`

```
🔧 构建师 (Build) — 请选择诊断方式：

  1. 定位构建错误 — 分析第一条真实报错，给出修复方案
  2. 依赖诊断 — 检查依赖版本、链接、环境配置问题
  3. 配置修复 — 修复 CMake/Cargo/go.mod 等构建配置
  4. 完整诊断 — 从错误定位到修复验证一站式处理
```

### 3.6 Qt 实现者 `agents/qt/task-implementer.md`

继承通用实现者菜单，增加 Qt 特有项：

```
💻 Amelia (Qt) — 请选择处理方式：

  1. 修复 Bug — 按 Story AC 逐条修复 Qt 相关缺陷
  2. 实现新功能 — 按 Story 执行 Qt 功能开发
  3. 代码重构 — 重构 Qt 代码，检查信号槽/生命周期/MOC
  4. 快速开发 — 小改动，跳过 Story 创建
  5. UI 调试 — 分析布局/sizePolicy/信号槽连接/界面异常
```

### 3.7 Qt 测试官 `agents/qt/test-engineer.md`

```
🧪 测试官 (Qt) — 请选择：

  1. 设计测试方案 — Qt 测试矩阵（QTest/CTest/smoke test）
  2. 生成测试代码 — 生成 QTest 测试用例
  3. 审查现有测试 — 审查 Qt 测试覆盖率与事件循环处理
```

### 3.8 Qt UI 审查官 `agents/qt/ui-reviewer.md`

```
🎨 UI 审查官 (Qt) — 请选择审查类型：

  1. 布局审查 — sizePolicy、间距、缩放行为、对话框边界
  2. 交互审查 — 信号槽绑定、焦点切换、状态反馈
  3. 一致性审查 — 控件命名、图标风格、文案规范
  4. 完整审查 — 布局 + 交互 + 一致性一次完成
```

---

## 4. 实施步骤

| # | 内容 | 涉及文件 | 工作量 |
|---|------|---------|--------|
| 1 | 通用实现者加菜单 | `agents/universal/task-implementer.md` | 小 |
| 2 | 规划师加菜单 | `agents/universal/feature-planner.md` | 小 |
| 3 | 审查官加菜单 | `agents/universal/code-reviewer.md` | 小 |
| 4 | 测试官加菜单 | `agents/universal/test-engineer.md` | 小 |
| 5 | 构建师加菜单 | `agents/universal/build-doctor.md` | 小 |
| 6 | Qt 实现者加菜单（含 UI 调试项） | `agents/qt/task-implementer.md` | 小 |
| 7 | Qt 测试官加菜单 | `agents/qt/test-engineer.md` | 小 |
| 8 | Qt UI 审查官加菜单 | `agents/qt/ui-reviewer.md` | 小 |
| 9 | 其他语言（python/node/rust/go）测试官同步 | `agents/*/test-engineer.md` | 小 |
| 10 | 更新 agent-index.md 说明菜单功能 | `docs/agent-index.md` | 极小 |

**总工作量：** 极小（约 1 天）——纯 Markdown 改动，不涉及任何 Python/JS 代码

---

## 5. 与现有架构的关系

### 5.1 与 review 门控的关系

菜单在"激活问候后"展示，不影响 review 门控流程。review 门控仍然是 `task-implementer-core.md` 中规定的强制步骤（标记 passed 前必须审查通过）。

### 5.2 与 dev 路由的关系

`/animus-dev` 的四路路由（debug/fast/light/full）是命令层路由，Agent 菜单是 Agent 层子路由，两者互补：

```
/animus-dev（命令层：选择开发路径）
  ├── fast-path → 调用 task-implementer（Agent 层：选择具体处理方式）
  │                ├── 1. 修复 Bug
  │                ├── 2. 实现新功能
  │                └── 4. 快速开发
  └── full-path → 调用 feature-planner（Agent 层：选择规划方式）
                   ├── 1. 差距分析
                   └── 4. 完整流程
```

### 5.3 与分层配置覆盖的关系

菜单内容是硬编码在 SKILL.md 中的。未来如果实现了分层配置覆盖，菜单项可以从 TOML 读取，用户可自定义。第一阶段不做 TOML 化。

---

## 6. 工作量估算

| 阶段 | 内容 | 预估 |
|------|------|------|
| 通用层（5 个 universal Agent） | 每个加一段 Markdown 表格 | ~1.5h |
| Qt 层（3 个 Agent） | 在通用基础上加 Qt 特有项 | ~0.5h |
| 其他语言同步（python/node/rust/go） | 从通用复制、小幅调整 | ~0.5h |
| 文档更新 | agent-index.md 加说明 | ~0.2h |

**总工作量：** 极小（约 1 天），纯 Markdown

---

## 7. 验收标准

| # | 验收条件 | 验证方法 |
|---|---------|---------|
| 1 | 5 个 universal Agent 激活后展示编号菜单 | 逐个查看 Agent 文件中菜单段落 |
| 2 | 菜单使用数字（1 2 3 4）而非字母码 | grep 检查菜单段落 |
| 3 | 每个菜单项有编号 + 简短描述（≤15 字） | 人工审核 |
| 4 | 菜单前有规则说明"意图明确时跳过" | 人工审核 |
| 5 | Qt 实现者有第 5 项"UI 调试" | 查看文件 |
| 6 | agent-index.md 中有菜单功能说明 | 查看文件 |
