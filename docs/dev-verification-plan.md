---
type: reference
audience: maintainer
---

# 路线图新增功能 — 统一开发与验证计划

> 综合 `task-docs-quadrant.md`、`task-agent-menus.md`、`task-plugin-validator.md`
> 三个方案文档，按执行依赖顺序编排的统一开发与验证计划。
>
> **每步开发时必须参考 BMAD Method 的对应实现，不能只看方案文档。**
> BMAD 源码位于 `D:\code\BMAD-METHOD-6.10.0\BMAD-METHOD-6.10.0`。

---

## 执行顺序

```
Phase 1.3 文档四象限重组  ← 先做（不依赖其他任务）
   ↓
Phase 1.4 Agent 编号菜单  ← 次做（文档重组后改 Agent 文件更清晰）
   ↓
Phase 2.4 双模式验证器   ← 后做（可验证前两个步骤的改动，且需参考 BMAD 双模式验证设计）
```

---

## 第一阶段：文档四象限重组

> 方案文档：`docs/task-docs-quadrant.md`
> 估算：~2 天
> BMAD 参考源：`BMAD-METHOD-6.10.0/docs/` 全部目录结构和文档

### 开发步骤

| 步骤 | 内容 | 涉及文件 | BMAD 参考位置 | 参考要点 |
|------|------|---------|--------------|---------|
| 1.3.1 | 新建目录结构 | 创建 `tutorials/` `how-to/` `reference/` | BMAD `docs/` 目录整体 | BMAD 的四象限布局，注意 `tutorials/` `how-to/` `explanation/` `reference/` 各自有 `index.md` 入口 |
| 1.3.2 | 拆分命令详解 | `guide.md` 1.1 节 → `reference/commands.md` | BMAD `docs/reference/commands.md` | BMAD 命令文档用表格罗列每个命令的用途、用法、参数，注意对齐方式 |
| 1.3.3 | 拆分配置系统 | `guide.md` 1.2 节 → `reference/config-options.md` | BMAD `docs/reference/modules.md` | BMAD 的配置参考按模块分组，每个配置项有类型、默认值、说明 |
| 1.3.4 | 拆分测试说明 | `guide.md` 1.3 节 → `reference/testing.md` | BMAD `docs/reference/testing.md` | BMAD 测试文档含命令表、环境要求、示例 |
| 1.3.5 | 拆分底层机制 | → `explanation/` 各文件 | BMAD `docs/explanation/analysis-phase.md` | BMAD explanation 以"why"为导向，用段落而非列表解释设计决策 |
| 1.3.6 | 合并架构部分 | → 已有 `architecture.md` | BMAD 无架构页 | 以现有 architecture.md 为准，BMAD 的 `docs/_STYLE_GUIDE.md` 可参考文档风格 |
| 1.3.7 | 新建上手教程 | → `tutorials/getting-started.md` | BMAD `docs/tutorials/getting-started.md` | BMAD 教程含 :::note 提示框、前置条件清单、分步代码块、Next Step 引导 |
| 1.3.8 | 新建 how-to | 3 个初始 how-to 文件 | BMAD `docs/how-to/non-interactive-installation.md` | BMAD how-to 用"问题→方案→步骤"结构，每步有代码示例 |
| 1.3.9 | 新建导航入口 | `docs/README.md` | BMAD `docs/index.md` | BMAD 入口页用 `\| 类型 \| 目的 \|` 四象限表格 + "New Here?" + "Next Step" |
| 1.3.10 | 加 frontmatter | 所有 docs/ 文件 | BMAD 无强制 frontmatter | 按自身 `type` + `audience` 规范，BMAD 的 `---` frontmatter 含 `title` `description` `sidebar.order` |
| 1.3.11 | guide.md 标注 deprecated | guide.md 顶部 | BMAD `removals.txt` | BMAD deprecation 标注含替代方案指引 |

### 验收清单

| # | 验收项 | 验证方法 | 通过标准 |
|---|--------|---------|---------|
| V1.1 | 目录结构存在 | `ls docs/` | 出现 `tutorials/` `how-to/` `reference/` `explanation/` |
| V1.2 | 命令参考完整 | grep 检查 `reference/commands.md` | 覆盖全部 7 个斜杠命令 + engine CLI 子命令 |
| V1.3 | 配置参考完整 | 对比 `config_loader.py` 的键 | `reference/config-options.md` 覆盖所有配置段 |
| V1.4 | guide.md 内容不再缺失 | 对比拆分前后内容 | 所有章节已迁移到目标文件 |
| V1.5 | 导航表可访问 | 手动点击 `docs/README.md` 每个链接 | 全部 404-free |
| V1.6 | frontmatter 统一 | `grep -r "^type:" docs/` | 每个 .md 文件有 `type` 字段 |
| V1.7 | guide.md deprecated | 查看文件顶部 | 有明显的 deprecated 标记 |
| V1.8 | 回归：原有链接不失效 | `animus-engine.py validate` | 通过 |

---

## 第二阶段：Agent 编号菜单

> 方案文档：`docs/task-agent-menus.md`
> 估算：~1 天
> BMAD 参考源：`BMAD-METHOD-6.10.0/src/bmm-skills/` 中各 Agent 的 `customize.toml` 和 `SKILL.md`

### 开发步骤

| 步骤 | 内容 | 涉及文件 | BMAD 参考位置 | 参考要点 |
|------|------|---------|--------------|---------|
| 1.4.1 | 实现者菜单 | `agents/universal/task-implementer.md` | BMAD `bmm-skills/4-implementation/bmad-dev-story/SKILL.md` | BMAD 的 workflow 不展示菜单，但注意其 **HALT 协议**（明确说明"什么时候停"）和**Subagents 同步调用规则** |
| 1.4.2 | 规划师菜单 | `agents/universal/feature-planner.md` | BMAD `bmm-skills/2-plan-workflows/bmad-prd/SKILL.md` | BMAD 的 PRD skill 有"Three intents in one skill"模式——同一个 skill 支持 Create/Update/Validate 三种意图，对应你的菜单分支路由 |
| 1.4.3 | 审查官菜单 | `agents/universal/code-reviewer.md` | BMAD `core-skills/bmad-review-adversarial-general/SKILL.md` + `bmad-review-edge-case-hunter/SKILL.md` | BMAD 有独立的 adversarial review 和 edge case hunter skill，各自专注一个维度——参考其"审查维度拆分"思路来定义你的菜单项 |
| 1.4.4 | 测试官菜单 | `agents/universal/test-engineer.md` | BMAD `bmm-skills/4-implementation/bmad-qa-generate-e2e-tests/SKILL.md` | BMAD QA skill 明确约定"generate tests ONLY — no code review or story validation"——每个菜单项职责边界要清晰 |
| 1.4.5 | 构建师菜单 | `agents/universal/build-doctor.md` | BMAD `bmm-skills/` 中无直接对应 | 以自身架构为准，参考 BMAD 的 `activation_steps_prepend/append` 机制来设计诊断步骤的可扩展性 |
| 1.4.6 | Qt 实现者菜单 | `agents/qt/task-implementer.md` | 同上 universal 参考 + BMAD `bmm-skills/4-implementation/bmad-quick-dev/SKILL.md` | BMAD Quick Dev 的"小改动跳过 Story 创建"思路对应你的"快速开发"和 Qt 的"UI 调试"菜单项 |
| 1.4.7 | Qt 测试官菜单 | `agents/qt/test-engineer.md` | 同 1.4.4 | 同 universal 测试官参考 |
| 1.4.8 | Qt UI 审查官菜单 | `agents/qt/ui-reviewer.md` | BMAD 无 UI 审查 | 以自身架构为准 |
| 1.4.9 | 其他语言测试官同步 | `agents/*/test-engineer.md` | 同 1.4.4 | 同 universal 测试官参考 |
| 1.4.10 | 更新索引 | `docs/agent-index.md` | BMAD `docs/reference/agents.md` | BMAD Agent 参考页用表格列出所有 Agent 的 code/name/title/primary workflows |

### 验收清单

| # | 验收项 | 验证方法 | 通过标准 |
|---|--------|---------|---------|
| V2.1 | 5 个 universal Agent 有菜单 | `grep -c "请选择" agents/universal/*.md` | 5 个文件各至少 1 次 |
| V2.2 | Qt 实现者有 5 项 | 查看 `agents/qt/task-implementer.md` | 含"UI 调试"项 |
| V2.3 | 菜单使用数字编号 | 查看菜单段落 | 无字母码，全部 `1. 2. 3.` |
| V2.4 | 每项有描述 | 逐项审核 | 每项编号 + 描述（≤15 字） |
| V2.5 | 跳过规则存在 | 查看菜单段落的上下文 | 有"意图明确时跳过"说明 |
| V2.6 | 强制门控不受影响 | 查看 `base/task-implementer-core.md` | review 门控段落未被改动 |
| V2.7 | 文档索引已更新 | 查看 `docs/agent-index.md` | 有菜单功能说明 |

### 菜单项汇总速查

| Agent | 1 | 2 | 3 | 4 | 5 |
|-------|---|---|---|---|---|
| 实现者 | 修复 Bug | 新功能 | 重构 | 快速开发 | — |
| 规划师 | 差距分析 | 任务拆分 | 更新术语 | 完整流程 | — |
| 审查官 | 全面审查 | 安全专项 | 性能专项 | 仅测试覆盖 | — |
| 测试官 | 设计方案 | 生成测试 | 审查测试 | — | — |
| 构建师 | 定位错误 | 依赖诊断 | 配置修复 | 完整诊断 | — |
| Qt 实现者 | 修复 Bug | 新功能 | 重构 | 快速开发 | UI 调试 |
| Qt 测试官 | 设计方案 | 生成测试 | 审查测试 | — | — |
| Qt UI 审查 | 布局审查 | 交互审查 | 一致性审查 | 完整审查 | — |

---

## 第三阶段：双模式验证器

> 方案文档：`docs/task-plugin-validator.md`
> 估算：~3-5 天
> BMAD 参考源：确定性部分参考 `BMAD-METHOD-6.10.0/tools/validate-skills.js`，语义部分参考 `BMAD-METHOD-6.10.0/tools/skill-validator.md`

### 开发步骤

#### 3a：确定性验证器脚本

| 步骤 | 内容 | 涉及文件 | BMAD 参考位置 | 参考要点 |
|------|------|---------|--------------|---------|
| 2.4.1 | 实现 R1 — plugin.json 命令一致性 | `scripts/plugin-validator.py` | BMAD `validate-skills.js` 的 SKILL-01 规则 | BMAD 用 `--json` 输出模式，每条规则独立判定，不因一条失败而跳过其余 |
| 2.4.2 | 实现 R2 — Agent 定义完整性 | `scripts/plugin-validator.py` | BMAD `validate-skills.js` 的 SKILL-02/03（frontmatter 必含 name + description） | BMAD 规则不直接写死路径，而是用 glob 发现所有 skill 目录再逐一检查 |
| 2.4.3 | 实现 R3 — Hooks 脚本存在性 | `scripts/plugin-validator.py` | BMAD 的 PATH-02 规则（引用路径可解析） | BMAD 用 `path.resolve` + `fs.existsSync`，Python 端用 `os.path.exists` |
| 2.4.4 | 实现 R4 — Agent 索引完整性 | `scripts/plugin-validator.py` | BMAD 无直接对应（BMAD 无 agent-index） | 以自身架构为准 |
| 2.4.5 | 实现 R5 — Rule 文件合法性 | `scripts/plugin-validator.py` | BMAD SKILL-04（文件结构合规性） | BMAD 检查 frontmatter 合法后还会验证 description 长度 ≥10 |
| 2.4.6 | 实现 R6 — 同语言组职责重叠 | `scripts/plugin-validator.py` | BMAD SKILL-06（skills 不重复） | BMAD 检查同一 module 内不出现两个同 code 的 skill |
| 2.4.7 | 实现 R7 — 孤立文件检测 | `scripts/plugin-validator.py` | BMAD 无直接对应 | 以自身架构为准 |
| 2.4.8 | 实现 R8 — 配置字段声明一致性 | `scripts/plugin-validator.py` | BMAD 无直接对应 | 以自身架构为准 |
| 2.4.9 | 实现输出模式 | `scripts/plugin-validator.py` | BMAD `validate-skills.js` 的 `--json` 输出格式 | BMAD 的 JSON 输出包含每条规则的 `status: passed/failed/warning` + `detail` 字段 |
| 2.4.10 | 注册到 animus-engine.py | `scripts/animus-engine.py` | BMAD CLI 无子命令模式 | 以自身架构为准 |

#### 3b：语义验证器文档

| 步骤 | 内容 | 涉及文件 | BMAD 参考位置 | 参考要点 |
|------|------|---------|--------------|---------|
| 2.4.11 | 撰写 S1 — 描述准确性 | `docs/plugin-validator-guide.md` | BMAD `skill-validator.md` | BMAD 的 `# Definitions` 段定义了"file path" "skill root"等术语，先定义术语再写规则 |
| 2.4.12 | 撰写 S2 — 职责不重叠 | `docs/plugin-validator-guide.md` | BMAD `skill-validator.md` SKILL-06 | BMAD 同时用确定性 + 推断规则重叠——你的语义规则也应注明"确定性规则已检查的部分可以跳过" |
| 2.4.13 | 撰写 S3 — 规则不矛盾 | `docs/plugin-validator-guide.md` | BMAD `skill-validator.md` 的 WF-03（workflow 一致性） | BMAD 检查 step 引用是否可解析到目标文件的 heading |
| 2.4.14 | 撰写 S4 — 降级路径声明 | `docs/plugin-validator-guide.md` | BMAD `skill-validator.md` 的 STEP-02/03 | BMAD 要求每个命令式步骤声明 fallback |
| 2.4.15 | 撰写 S5 — 激活步骤顺序 | `docs/plugin-validator-guide.md` | BMAD `skill-validator.md` 的 SEQ-01/02 | BMAD 检查 steps 按数字前缀顺序排列 |
| 2.4.16 | 撰写 S6 — 配置项存在性 | `docs/plugin-validator-guide.md` | BMAD 无直接对应 | 以自身架构为准 |
| 2.4.17 | 撰写 S7 — 文档同步 | `docs/plugin-validator-guide.md` | BMAD 无直接对应 | 以自身架构为准 |
| 2.4.18 | 撰写 S8 — 国际化一致性 | `docs/plugin-validator-guide.md` | BMAD 无直接对应 | 以自身架构为准 |

#### 3c：集成与测试

| 步骤 | 内容 | 涉及文件 | BMAD 参考位置 | 参考要点 |
|------|------|---------|--------------|---------|
| 2.4.19 | Hook 集成 | `hooks/hooks.json` | BMAD `.claude-plugin/hooks.json` | BMAD 钩子注册格式同你的 hooks.json |
| 2.4.20 | CLAUDE.md 指引 | `CLAUDE.md` | BMAD `CLAUDE.md` 开发约定 | BMAD 的 validate 命令同样在 CLAUDE.md 中列出 |
| 2.4.21-25 | 测试 | `tests/test_plugin_validator.py` | BMAD `test/test-validate-skills.js` | BMAD 测试用 mock 的 skill 目录（valid + invalid）做 fixtures——你的测试也应准备 `tests/fixtures/plugin-valid/` 和 `plugin-invalid/` |

### 确定性规则速查

| 规则 | 检查内容 | 严重度 | 可自动修复 | BMAD 对应规则 |
|------|---------|--------|-----------|-------------|
| R1 | plugin.json 命令文件存在性 | error | ❌ | PATH-02 |
| R2 | Agent 定义完整性（frontmatter） | error | ✅ 补占位 | SKILL-02/03 |
| R3 | Hooks 脚本存在性 | error | ❌ | PATH-02 |
| R4 | Agent 索引完整性 | warning | ✅ 追加占位行 | 无 |
| R5 | Rule 文件 frontmatter 合法性 | error | ✅ 修复 YAML | SKILL-04 |
| R6 | 同语言组职责重叠 | warning | ❌ | SKILL-06 |
| R7 | 孤立文件 | warning | ❌ | 无 |
| R8 | 配置字段声明一致性 | warning | ❌ | 无 |

### 验收清单

| # | 验收项 | 验证方法 | 通过标准 |
|---|--------|---------|---------|
| V3.1 | 正常插件通过 | `python scripts/plugin-validator.py` | 输出 PASSED，exit 0 |
| V3.2 | 缺失 frontmatter 检测 | 故意删除一个 Agent 的 description | FAILED + 具体路径 |
| V3.3 | Hooks 引用失效检测 | 修改 hooks.json 指向不存在文件 | FAILED |
| V3.4 | --json 输出有效 | `python scripts/plugin-validator.py --json` | 有效 JSON |
| V3.5 | --fix 可修复 | `--fix` 补全缺失 frontmatter | 文件被正确修改 |
| V3.6 | --strict 模式 | warning 级别在 --strict 下 exit 1 | exit 1 |
| V3.7 | engine 集成 | `python animus-engine.py validate --plugin` | 同 V3.1 |
| V3.8 | 语义规则可读 | AI 读 `plugin-validator-guide.md` 后审查 | 输出有意义报告 |
| V3.9 | Hook 不阻塞写 | 修改文件触发 PostToolUse | exit 0，不阻塞 |
| V3.10 | 测试全部通过 | `pytest tests/test_plugin_validator.py` | 全部通过 |

---

## 时间线总览

```
周次      Phase 1.3（文档）          Phase 1.4（菜单）          Phase 2.4（验证器）
第 1 天   1.3.1-1.3.4 拆分基础
          → 先看 BMAD docs/ 目录结构
第 2 天   1.3.5-1.3.8 拆分+新建
          → 参考 BMAD 教程/how-to 写法
第 3 天   1.3.9-1.3.11 收尾+验收     1.4.1-1.4.5 通用层
          → 参考 BMAD index.md 导航     → 参考 BMAD skill 的意图路由
第 4 天                             1.4.6-1.4.10 语言层+验收  2.4.1-2.4.5 R1-R5
                                                               → 看 BMAD validate-skills.js
第 5 天                                                  2.4.6-2.4.10 R6-R8+CLI
                                                          → 看 BMAD --json 输出格式
第 6 天                                                  2.4.11-2.4.18 语义规则
                                                          → 看 BMAD skill-validator.md
第 7 天                                                  2.4.19-2.4.25 集成+测试
                                                          → 看 BMAD test fixtures
```

### 每阶段开始前的标准动作

进入对应阶段的开发前，先读 BMAD 参考源：

```
阶段 1（文档）开始前：
  1. 浏览 BMAD docs/ 目录结构
  2. 读 index.md 的导航表
  3. 挑一个 tutorial 和一个 how-to 读全文

阶段 2（菜单）开始前：
  1. 读 BMAD bmm-skills/ 下任意一个 customize.toml 的菜单定义
  2. 读对应 SKILL.md 的 "On Activation → Step 8: Dispatch or Present the Menu"

阶段 3（验证器）开始前：
  1. 读 BMAD tools/validate-skills.js（重点：规则注册 + --json 输出）
  2. 读 BMAD tools/skill-validator.md（重点：双模式协作方式）
  3. 读 BMAD test/test-validate-skills.js（重点：fixture 目录结构）
```

---

## 回归验证

三个阶段全部完成后，执行全量回归：

| # | 回归项 | 验证方法 |
|---|--------|---------|
| R1 | 插件自检 | `python scripts/plugin-validator.py --strict` |
| R2 | 状态机校验 | `python animus-engine.py validate` |
| R3 | 测试套件 | `pytest tests/` |
| R4 | 文档导航 | 从 `docs/README.md` 遍历所有链接 |
| R5 | 菜单不破坏 Agent 行为 | 查看每个 Agent 的 review 门控步骤未被修改 |
