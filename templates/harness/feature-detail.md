# Feature Detail

## Txxx - 功能名称
状态: pending | 优先级: P0 | 依赖: 无

### 子功能
- [ ] 子功能 1
- [ ] 子功能 2

### 方案描述
{设计思路、架构方案、实现策略的详细说明。描述"怎么做"，而不仅仅是"做什么"。}

### 涉及文件
- `path/to/file1` — 改动说明
- `path/to/file2` — 改动说明

### 验收标准
1. 标准 1
2. 标准 2

---

## T025 - Handoff
状态: pending | 优先级: P0 | 依赖: T024

### 子功能
- [ ] /harness-code-handoff 命令
- [ ] /harness-code-continue 命令
- [ ] handoff.json 格式定义
- [ ] session-catchup.py 增强
- [ ] plugin.json 注册命令

### 方案描述
Handoff 机制用于跨会话上下文保存与恢复。

**保存阶段（/harness-code-handoff）：**
1. 读取当前 features.json 中的活跃任务、已完成任务、阻塞任务
2. 收集 findings.md、task_plan.md、feature-detail.md 中的上下文
3. 将上述信息序列化为 `.claude/harness-cc/handoff.json`
4. handoff.json 包含：context / tasks / findings / files / timestamp / status 字段
5. 完成后打印恢复命令提示

**恢复阶段（/harness-code-continue）：**
1. 读取 handoff.json，验证 status 是否为 "saved"（已加载过的标记 "loaded" 防重复）
2. 恢复当前活跃任务状态到 features.json
3. 打印恢复摘要：当前进度、未完成任务、阻塞项
4. 标记 handoff.json 为 loaded 状态

**session-catchup.py 增强：**
- 增加 handoff.json 检测能力，优先于 features.json 恢复
- 输出格式兼容现有 5 问检查框架

### 涉及文件
- `commands/harness-code-handoff.md` — 新命令，handoff 编排
- `commands/harness-code-continue.md` — 新命令，continue 编排
- `.claude-plugin/plugin.json` — 注册两个新命令
- `templates/harness/handoff.json` — handoff 数据格式模板
- `scripts/session-catchup.py` — 增强 handoff.json 读取能力

### 验收标准
1. /harness-code-handoff 生成格式正确的 handoff.json
2. /harness-code-continue 读取 handoff.json 并恢复上下文
3. 加载后标记 status=loaded，防止重复加载
4. session-catchup.py 能检测并提示 handoff.json 存在

---

## T026 - Domain Lexicon
状态: pending | 优先级: P0 | 依赖: T024

### 子功能
- [x] domain-lexicon.md 模板
- [x] feature-planner 术语提取指令
- [x] task-implementer 术语追加指令

### 方案描述
领域术语表（Domain Lexicon）用于统一项目中的业务概念表达，避免同义不同名导致的沟通混乱。

**术语来源与提取时机：**
1. **Grilling 阶段**（feature-planner）：Q1 验收标准中出现的业务概念、Q5 架构约束中的技术术语
2. **实现阶段**（task-implementer）：遇到新的业务领域术语时追加

**术语表文件结构：**
- 位置：`.claude/harness-cc/domain-lexicon.md`
- 格式：Markdown 表格，列：术语 | 英文 | 定义 | 别名 | 来源（I{N}-T{NNN}）
- 不存在时参考 `templates/harness/domain-lexicon.md` 创建

**写入规则：**
- 只追加不删除（append-only）
- 每个术语记录可追溯来源任务
- 迭代结束时可以评审归档

### 涉及文件
- `templates/harness/domain-lexicon.md` — 新建模板
- `agents/universal/feature-planner.md` — 追加术语提取指令
- `agents/base/task-implementer-core.md` — 追加术语追加指令

### 验收标准
1. domain-lexicon.md 模板存在且格式正确
2. feature-planner 包含 Grilling 后的术语提取指令（关注 Q1/Q5）
3. task-implementer-core 包含术语追加指令（格式：术语/英文名/定义/别名/来源）

---

## T027 - ADR
状态: pending | 优先级: P0 | 依赖: T024

### 子功能
- [x] ADR 模板 + 目录
- [x] task-implementer-core.md ADR 指令
- [x] 6 个 architect agent ADR 指令

### 方案描述
架构决策记录（Architecture Decision Record）用于持久化记录项目的关键架构决策及其背景。

**创建时机与责任人：**
1. **设计阶段**（Architect agent）：
   - 框架选型（如 Qt 6 vs Qt 5、C++17 vs C++20）
   - 模块划分方案（如 MVC vs MVVM、分层 vs 六边形）
   - 关键接口约定（如信号槽设计、跨线程边界）
   - 非功能性约束妥协（如内存 vs 性能权衡）
2. **实现阶段**（Implementer）：
   - 遇到方案文档未覆盖的架构级决策时补充

**ADR 文件结构：**
- 目录：`.claude/harness-cc/adr/`
- 命名：`ADR-{NNN}-{简短标题}.md`
- Frontmatter：日期、迭代、状态（提议/已采纳/已弃用）、关联任务
- 正文：上下文（决策背景）、决策（具体内容）、备选方案（至少 2 个方案+理由）、后果（正面+负面）

**版本控制：**
- ADR 文件与代码一起提交，随项目版本历史可追溯
- 已弃用的 ADR 不删除，仅修改状态为"已弃用"，保留历史记录

### 涉及文件
- `templates/harness/adr/ADR-000-模板.md` — 新建模板
- `templates/harness/adr/README.md` — 新建索引文件
- `agents/base/task-implementer-core.md` — 追加 ADR 记录指令
- `agents/qt/architect.md` — 追加 ADR 创建指令
- `agents/cpp-cmake/architect.md` — 追加 ADR 创建指令
- `agents/python/architect.md` — 追加 ADR 创建指令
- `agents/node/architect.md` — 追加 ADR 创建指令
- `agents/rust/architect.md` — 追加 ADR 创建指令
- `agents/go/architect.md` — 追加 ADR 创建指令

### 验收标准
1. ADR 模板和 README 索引存在
2. task-implementer-core 包含 ADR 记录指令（创建位置、编号规则、内容结构）
3. 6 个语言 architect 均包含 ADR 创建指令（设计完成后记录关键架构决策）
