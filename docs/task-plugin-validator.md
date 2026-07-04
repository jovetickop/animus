---
type: reference
audience: plugin-developer
---

# 双模式验证器（Dual-Mode Plugin Validator）

> 为 animus 插件自身引入"确定性 + 语义"两阶段验证，确保插件结构的完整性和 AI 行为的质量一致性。
> 参考 BMAD Method v6.10.0 的 `validate-skills.js`（确定性规则） + `skill-validator.md`（LLM 可读规则）双模式。

---

## 1. 背景与动机

### 现状

当前 animus 只有一条验证路径：

```
scripts/engine/cmd_validate.py
  └── 校验 .claude/animus/features.json 的结构
       └── 字段完整性、状态合法性、循环依赖检测、SPEC 4 法则
```

这条路径仅覆盖**目标工程的任务状态文件**，完全不触及**插件自身**的完整性：

| 未被检查的内容 | 可能出什么问题 |
|---------------|--------------|
| Agent 定义文件缺少 frontmatter | AI 助手无法发现该 Agent，用户调用时报错 |
| `hooks/hooks.json` 引用了不存在的脚本 | 钩子静默失败，格式化/门控失效 |
| `docs/agent-index.md` 有新增 Agent 但未记录 | 用户不知道有该 Agent |
| Agent 描述模糊或职责重叠 | AI 选错 Agent，上下文浪费 |
| Rule 文件给出了矛盾的指导 | AI 行为不一致 |

### 目标

引入双模式验证器，两条路径互补：

```
验证入口 →

  ├── 确定性模式（脚本驱动，exit code 反馈）
  │       scripts/plugin-validator.py
  │       规则：文件存在性 → frontmatter 完整性 → 引用可解析 → 无孤立文件
  │       输出：人类可读报告 / JSON 报告 / exit 0/1
  │       用途：CI 门禁、pre-commit、安装后自检
  │
  └── 语义模式（文档驱动，AI 审查）
          docs/plugin-validator-guide.md
          规则：Agent 描述准确？Rule 不矛盾？降级路径声明？
          用途：大规模重构后的质量门禁、新贡献者提交前的自检
```

---

## 2. 设计目标

| 维度 | 确定性模式 | 语义模式 |
|------|-----------|---------|
| 检查内容 | 结构完整性（存在性、格式、引用） | 语义正确性（描述、一致性、完整性） |
| 执行方式 | `python scripts/plugin-validator.py` | AI 读取 `plugin-validator-guide.md` 后审查 |
| 判定标准 | pass/fail（硬门禁） | 满足/建议修改/必须修复（三级） |
| 自动化程度 | 完全自动 | 需要 AI 参与 |
| 使用时机 | CI、pre-commit、install | 重构后、新贡献者提交前 |
| 输出格式 | 文本 / JSON / exit code | Markdown 审查报告 |

---

## 3. 确定性验证器（plugin-validator.py）

### 3.1 与现有验证的关系

```
scripts/
  animus-engine.py          ← 统一 CLI 入口
    engine/
      cmd_validate.py        ← 现有：校验 features.json
  plugin-validator.py       ← 新增：校验插件自身结构
                              （在 animus-engine.py 中注册为
                               `validate --plugin` 子命令）
```

**不合并到 cmd_validate.py 的理由：**
- cmd_validate 验证的是**目标工程的运行时状态**（features.json）
- plugin-validator 验证的是**插件自身的发布质量**（Agent/Rule/Hook 完整性）
- 两个验证的生命周期不同：前者每次会话运行，后者在插件修改后运行

### 3.2 规则清单

#### R1 — plugin.json 命令一致性

检查 `plugin.json` 的 `commands` 数组中每条路径对应的文件是否存在。

```python
# 伪代码
for cmd_path in plugin_json["commands"]:
    assert os.path.exists(resolve(cmd_path))
```

**失败示例：** 删除了 `commands/animus-party.md` 但忘了更新 `plugin.json`。

---

#### R2 — Agent 定义完整性

遍历 `agents/` 下所有子目录，检查：
- 每个 Agent 目录必须包含 skil.md（或同名定义文件）
- 文件的 YAML frontmatter 必须包含 `name` 和 `description` 字段
- `description` 必须 ≥ 10 个字符（防止占位符）

```python
# 伪代码
for agent_dir in agents/*/:
    assert has_definition_file(agent_dir)
    fm = parse_frontmatter(definition_file)
    assert fm.get("name")
    assert len(fm.get("description", "")) >= 10
```

**失败示例：** 新建 `agents/rust/code-reviewer.md` 时忘记写 description。

---

#### R3 — Hooks 脚本存在性

检查 `hooks/hooks.json` 中注册的所有 `command` 路径对应的脚本文件是否存在（python 和 bash 分支分别检查）。

```python
# 伪代码
for hook_event in hooks_json["hooks"]:
    for hook in hook_event["hooks"]:
        cmd = hook["command"]
        for ref in extract_script_paths(cmd):
            assert os.path.exists(ref) or ref.startswith("${")  # 环境变量引用跳过
```

**失败示例：** 重命名了 `hooks/scripts/format-all.py` 但忘了更新 `hooks.json`。

---

#### R4 — Agent 索引完整性

检查 `docs/agent-index.md` 中的 Agent 列表与 `agents/` 目录下的实际 Agent 一一对应：
- index 中记录的每个 Agent 在 `agents/` 下有对应目录/文件
- `agents/` 下的每个 Agent 在 index 中有记录

```python
# 伪代码
index_agents = parse_index_table("docs/agent-index.md")
actual_agents = discover_agents("agents/")
assert set(index_agents) == set(actual_agents)
```

**失败示例：** 新增了 `agents/frontend/ui-reviewer.md` 但忘了更新 `agent-index.md`。

---

#### R5 — Rule 文件合法性

遍历 `rules/` 下所有 `.md` 文件，检查：
- 文件有合法的 YAML frontmatter
- 文件内容不为空（至少 50 个有效字符）

```python
# 伪代码
for rule_file in glob("rules/**/*.md"):
    fm = try_parse_yaml_frontmatter(rule_file)
    assert fm is not None
```

**失败示例：** 新建 rule 文件时 frontmatter 格式错误，AI 无法解析。

---

#### R6 — 同语言组内职责不重叠

在同一 `agents/{lang}/` 目录下，检查所有 Agent 的 `description` 和 `title` 字段，不应有显著语义重叠。

```python
# 伪代码
for lang in language_groups:
    descriptions = get_all_descriptions(lang)
    for a, b in pairs(descriptions):
        assert similarity(a, b) < THRESHOLD
```

> 注：此规则作为 warning（不阻断 CI），仅标记给审查者。

---

#### R7 — 无孤立文件

检查 `agents/` 和 `rules/` 目录中是否存在未被任何索引或引用链覆盖的文件。

```python
# 伪代码
all_files = glob("agents/**/*.md") + glob("rules/**/*.md")
referenced = resolve_all_references(["docs/agent-index.md", hooks_json, plugin_json])
orphans = set(all_files) - set(referenced)
assert len(orphans) == 0  # warning if > 0
```

**失败示例：** 重构后遗留了旧的 Agent 文件但不再被引用。

---

#### R8 — Config 字段声明一致性

检查 `scripts/config_loader.py` 中读取的配置键是否在config.toml 中有对应默认值声明。

```python
# 伪代码
config_keys = extract_config_keys("scripts/config_loader.py")
toml_keys = extract_toml_keys(".claude/animus/config.toml")
for key in config_keys:
    assert key in toml_keys  # warning if not found
```

---

### 3.3 CLI 接口

```
python scripts/plugin-validator.py            # 人类可读输出
python scripts/plugin-validator.py --strict   # CI 模式，任何 warning 也 exit 1
python scripts/plugin-validator.py --json     # JSON 报告（供工具消费）
python scripts/plugin-validator.py --fix      # 自动修复（仅缺失 frontmatter 等简单项）
```

**退出码：**

| 退出码 | 含义 | 触发条件 |
|--------|------|---------|
| 0 | 完全通过 | 所有规则（含 warning）通过 |
| 0 | 有 warning 但通过 | --strict 未启用，只有 warning |
| 1 | 失败 | 有硬错误，或 --strict 模式下有 warning |

**JSON 输出格式：**

```json
{
  "version": "1.0",
  "passed": true,
  "strict": false,
  "auto_fixed": 0,
  "rules": {
    "R1": { "status": "passed", "detail": "所有 command 引用有效" },
    "R2": { "status": "failed", "detail": "agents/go/code-reviewer.md: 缺少 description" },
    "R3": { "status": "passed", "detail": "" },
    "R4": { "status": "warning", "detail": "agents/frontend/ui-reviewer.md 未在 agent-index.md 中记录" },
    "R5": { "status": "passed", "detail": "" },
    "R6": { "status": "passed", "detail": "" },
    "R7": { "status": "passed", "detail": "" },
    "R8": { "status": "passed", "detail": "" }
  },
  "errors": ["agents/go/code-reviewer.md: 缺少 description"],
  "warnings": ["agents/frontend/ui-reviewer.md 未在 agent-index.md 中记录"],
  "auto_fixes": []
}
```

### 3.4 自动修复支持（--fix 模式）

对以下简单问题可自动修复：

| 规则 | 可修复内容 |
|------|-----------|
| R2（缺失 description） | 写入占位符 `"description": "TBD — 请填写"` |
| R4（index 缺失条目） | 在 agent-index.md 末尾追加占位行 |
| R5（frontmatter 格式异常） | 尝试修复常见 YAML 格式错误 |

复杂问题（职责重叠、孤立文件）只报告不修复。

---

## 4. 语义验证器（plugin-validator-guide.md）

### 4.1 文档定位

`docs/plugin-validator-guide.md` 是一份**给 AI 助手阅读的规则文档**，不是给开发者的操作手册。它的目标读者是 AI 编码助手（Claude Code 等），指导其在插件修改后执行质量审查。

### 4.2 规则清单

#### S1 — 描述准确性

每条 Agent 的 `description` frontmatter 必须在 1 句话内准确说明"AI 助手在什么场景下应该调用这个 Agent"。

| 等级 | 示例 |
|------|------|
| ✅ 正确 | "Use when the user reports a segfault or stack overflow in a C++ Qt application" |
| ⚠️ 模糊 | "C++ debugging"（太短，AI 不知道怎么触发） |
| ❌ 错误 | 直接复制了其他 Agent 的描述（导致路由冲突） |

**检查方法：** 对于每个 Agent，用该 description 作为搜索词在项目内搜索——如果多个 Agent 返回，说明描述不够独特。

---

#### S2 — 职责不重叠

同一语言组内的 Agent 职责描述不应出现语义重叠。如果两个 Agent 都说"修复编译错误"，需要合并或明确分工。

**检查方法：** 按语言组分组读取 description，标记语义相似度 > 70% 的对。

---

#### S3 — 规则不矛盾

同一语言组的 `rules/` 中，两条规则不应给出冲突的指导。

| 冲突示例 | 说明 |
|---------|------|
| Rule A: "使用 snake_case 命名" | 两条规则如果在同一个组内同时生效，AI 会困惑 |
| Rule B: "使用 camelCase 命名" | |

**检查方法：** 按语言组读取 rules，标记明显的相反指令对。

---

#### S4 — 外部工具依赖声明降级路径

如果 Agent 或 Rule 在步骤中引用了外部工具（如 `clang-format`、`black`、`cargo fmt`），必须声明该工具不可用时的降级行为。

| 等级 | 示例 |
|------|------|
| ✅ 正确 | "Run `clang-format`...如果不可用则跳过格式化" |
| ❌ 缺漏 | "Run `cargo fmt`"（无 fallback） |

**检查方法：** 扫描 Agent 文件中的 shell 命令引用，检查同一命令是否有对应的 hook 降级脚本。

---

#### S5 — Agent 激活步骤逻辑顺序

Agent 的激活步骤（On Activation）应该按依赖顺序排列。后一步依赖前一步的输出时，顺序不能颠倒。

| 正确顺序 | 错误顺序 |
|---------|---------|
| 1. 解析配置 | 1. 问候用户 |
| 2. 加载持久事实 | 2. 解析配置（先问候再读配置，语言可能不一致） |
| 3. 问候用户 | |

**检查方法：** 检查 Agent 定义中是否存在"先使用、后定义"的变量引用。

---

#### S6 — 配置项存在声明

Agent 或 Rule 中引用的配置变量（如 `{communication_language}`、`{user_skill_level}`）必须在 `config.toml` 中有对应的默认值声明。

**检查方法：** 提取 Agent 文件中的所有 `{variable}` 引用，与 `config.toml` 的键集合对比。

---

#### S7 — 文档与代码同步

当 Agent/Rule 的行为变更时，对应的索引文档（`docs/agent-index.md`）、路线图（`bmad-optimization-roadmap.md`）、和架构文档（`architecture.md`）应同步更新。

**检查方法：**
1. 列出本次变更涉及的文件
2. 检查变更是否影响了 Agent 的触发条件、输入输出、或依赖关系
3. 如果是，确认索引文档已更新

---

#### S8 — 国际化一致性

如果 Agent 内容包含中文注释，那么相关的用户可见输出（问候、错误提示）也应该是中文。中英混用的输出需要统一。

**检查方法：** 扫描 Agent 文件中 > 20 字的可见文本段，检查是否同一种语言内混入了另一种语言的单词（技术术语除外，如 `git`、`CMake`、`features.json`）。

### 4.3 使用方式

AI 助手在以下场景应主动阅读 `plugin-validator-guide.md`：

1. **大规模修改后**：新增/修改了 5 个以上的 Agent 或 Rule 文件
2. **新增语言支持后**：`agents/{lang}/` 完整目录创建后
3. **提交 PR 前**：作为自我审查清单
4. **代码审查时**：审查者读取 guide，逐条检查提交的代码

---

## 5. 集成方案

### 5.1 注册到 animus-engine.py

在 `scripts/animus-engine.py` 的 `validate` 子命令中增加 `--plugin` 标志：

```bash
# 现有：校验目标工程的 features.json
python animus-engine.py validate

# 新增：校验插件自身结构
python animus-engine.py validate --plugin

# 新增：插件校验 + CI 严格模式
python animus-engine.py validate --plugin --strict
```

### 5.2 Hooks 集成

在 `hooks/hooks.json` 的 PostToolUse 中增加一个轻量钩子：

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "python \"${CLAUDE_PLUGIN_ROOT}/scripts/plugin-validator.py\" 2>/dev/null || exit 0",
      "timeout": 5
    }
  ]
}
```

> 仅在有变更涉及 `agents/`、`rules/`、`hooks/`、`plugin.json` 时建议触发。
> 默认 exit 0 不阻塞写操作。

### 5.3 CI 集成

在项目根目录的 CI 配置（如有）或 pre-commit hook 中加入：

```bash
# pre-commit 或 CI 步骤
python scripts/plugin-validator.py --strict
```

### 5.4 CLAUDE.md 指引

在 `CLAUDE.md` 中增加一条：

```markdown
## 插件自检

修改 Agent、Rule、Hook 后建议运行验证：
```bash
python scripts/plugin-validator.py
```

大规模重构后请 AI 读取 `docs/plugin-validator-guide.md` 执行语义审查。
```

---

## 6. 测试方案

### 6.1 单元测试

在 `tests/` 下新建 `test_plugin_validator.py`，覆盖：

| 测试用例 | 覆盖规则 | 预期结果 |
|---------|---------|---------|
| 正常目录结构 | R1-R8 | PASSED |
| 缺少 command 文件 | R1 | FAILED |
| Agent 缺少 frontmatter | R2 | FAILED |
| Hooks 引用不存在的脚本 | R3 | FAILED |
| Agent 未在 index 中记录 | R4 | WARNING |
| rules 文件 frontmatter 异常 | R5 | FAILED |
| 同语言组职责重叠 | R6 | WARNING |
| 孤立文件 | R7 | WARNING |
| --json 输出格式 | 全部 | 有效 JSON + exit code |
| --fix 自动修复 | R2/R4 | 文件被修复 |

### 6.2 测试数据

在 `tests/fixtures/` 下创建测试用的 mock 目录结构：

```
tests/fixtures/plugin-invalid/
  plugin.json（引用不存在的命令）
  agents/
    test-agent/
      skil.md（缺少 frontmatter）
  hooks/
    hooks.json（引用不存在的脚本）
```

```
tests/fixtures/plugin-valid/
  plugin.json（有效引用）
  agents/
    test-agent/
      skil.md（完整 frontmatter）
  hooks/
    hooks.json（引用存在脚本）
```

---

## 7. 工作量估算

| 阶段 | 内容 | 涉及文件 | 预估工作量 |
|------|------|---------|-----------|
| 1 | 新建 `plugin-validator.py`，实现 R1-R5（核心结构规则） | `scripts/plugin-validator.py` | 中 |
| 2 | 实现 R6-R8（语义指标 + 配置一致性） | `scripts/plugin-validator.py` | 小 |
| 3 | 实现 --json / --strict / --fix 模式 | `scripts/plugin-validator.py` | 小 |
| 4 | 注册到 `animus-engine.py validate --plugin` | `scripts/animus-engine.py` | 极小 |
| 5 | 新建 `docs/plugin-validator-guide.md`，撰写 S1-S8 | `docs/plugin-validator-guide.md` | 中 |
| 6 | Hook 集成 | `hooks/hooks.json` | 极小 |
| 7 | CLAUDE.md 指引 | `CLAUDE.md` | 极小 |
| 8 | 测试用例 | `tests/test_plugin_validator.py`、`tests/fixtures/` | 中 |
| 9 | 更新路线图 | `docs/bmad-optimization-roadmap.md` | 极小 |

**总工作量估算：** 中（约 3-5 天）

---

## 8. 验收标准

当以下条件全部满足时，该任务视为完成：

| # | 验收条件 | 验证方法 |
|---|---------|---------|
| 1 | `python scripts/plugin-validator.py` 在正常插件上输出 PASSED | 手动运行 |
| 2 | 故意破坏一个 Agent frontmatter 后，输出 FAILED 并指出具体问题 | 手动运行 |
| 3 | `python scripts/plugin-validator.py --json` 输出有效 JSON 且 exit code 符合预期 | 手动运行 |
| 4 | `python scripts/plugin-validator.py --fix` 能修复缺失的 frontmatter | 手动运行 |
| 5 | AI 读取 `docs/plugin-validator-guide.md` 后能输出一份有意义的审查报告 | 实际运行一次 |
| 6 | `python animus-engine.py validate --plugin --strict` 能通过 CI 门禁 | 手动运行 |
| 7 | 修改 Agent 文件后 Hook 自动运行验证（不阻塞写操作） | mock 测试 |
| 8 | `tests/test_plugin_validator.py` 全部测试通过 | `pytest tests/test_plugin_validator.py` |

---

## 9. 与现有路线图的关系

本任务作为 Phase 2（能力增强）的第 2.5 个子条目，位于"对抗性审查"之后、"多 IDE 适配"之前。

路线图更新后总览：

```
Phase 0 (基础设施)      Phase 1 (核心体验)      Phase 2 (能力增强)       Phase 3 (深度建设)
├── 配置系统（两层）     ├── 命名 Agent           ├── 工作流地图            ├── SPEC 内核 [✅]
├── 引擎脚本化          ├── Memlog 持久化        ├── 对抗性审查
                        ├── Party Mode           ├── 🆕 双模式验证器
                        └── Quick Dev            ├── 头脑风暴
                                                 └── 多 IDE 适配
```
