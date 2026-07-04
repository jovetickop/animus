# Feature Detail — 迭代 I2

## T033 - 归档脚本完善
状态: pending | 优先级: P0 | 依赖: 无

### 子功能
- [ ] 命名冲突保护：同名归档目录已存在时报错提示，不覆盖
- [ ] domain-lexicon.md 纳入归档文件列表

### 方案描述
**当前问题：**
1. `archive-iteration.py` 第 74 行使用 `os.makedirs(iter_dir, exist_ok=True)`，同名目录已存在时静默成功，用户无感知。
2. domain-lexicon.md 未加入 `files_to_archive` 列表，归档时会遗漏。

**改动方案：**
1. 用 `os.path.isdir()` 检查替换 `exist_ok=True`，目录存在时 `print` 错误并 `return 1`
2. 将 `"domain-lexicon.md"` 追加到 `files_to_archive` 列表
3. 在清理段（cleanup）添加 domain-lexicon.md 的清理逻辑

### 涉及文件
- `scripts/archive-iteration.py` — 命名冲突检查 + 归档列表扩展 + 清理扩展

### 验收标准
1. 同名目录已存在时脚本报错退出（exit 1），不静默覆盖
2. domain-lexicon.md 在归档时被复制到归档目录
3. domain-lexicon.md 在归档后被清理（从运行态移除）
4. 语法检查通过：`python -m py_compile scripts/archive-iteration.py`

---

## T034 - Domain Lexicon 初始化联动
状态: pending | 优先级: P0 | 依赖: 无

### 子功能
- [ ] animus-setup.ps1 在初始化时创建 domain-lexicon.md

### 方案描述
**当前问题：**
`animus-setup.ps1` 创建 features.json、project-config.json 等文件，但不创建 `domain-lexicon.md`。模板已存在于 `templates/animus/domain-lexicon.md`，但 setup 脚本未引用。

**改动方案：**
在 `animus-setup.ps1` 中新增初始化 domain-lexicon.md 的步骤（参考已有 features.json 初始化模式），写入空术语表结构（参考模板格式，不带示例条目）。

### 涉及文件
- `commands/animus-setup.ps1` — 新增 domain-lexicon.md 初始化步骤

### 验收标准
1. 运行 setup 后在 `.claude/animus/domain-lexicon.md` 生成空术语表
2. 已存在时不覆盖（幂等性）
3. 语法检查通过：`PowerShell PSParser.Tokenize`

---

## T035 - Grilling 互动式提问改造
状态: pending | 优先级: P0 | 依赖: 无

### 子功能
- [ ] animus-plan.md 中 Grilling 阶段使用 AskUserQuestion 工具

### 方案描述
**当前问题：**
`animus-plan.md` 的 Grilling 阶段使用纯文本逐问方式。用户期望使用 `AskUserQuestion` 工具进行互动式提问，提供结构化选项和自定义输入支持。

**改动方案：**
修改 `animus-plan.md` 中 Q1-Q7 的提问方式，使用 AskUserQuestion 工具：
- 每个问题提供 2-3 个默认选项 + 自定义输入（Other...）
- 保持与现有 plan-context.md 模板格式兼容
- 问题排序和内容不变

### 涉及文件
- `commands/animus-plan.md` — Grilling 提问方式改为 AskUserQuestion

### 验收标准
1. 每个 Grilling 问题都使用 AskUserQuestion 工具提问
2. 提供结构化选项供用户选择
3. 支持自定义输入（Other... 选项）
4. 回答格式与 plan-context.md 模板兼容
5. 无文档分支（7 问固定模板）和有文档分支（针对性追问）均改造

---

## T036 - 集成测试验收
状态: pending | 优先级: P0 | 依赖: T033, T034, T035

### 子功能
- [ ] 验证 T033 归档脚本改动的正确性
- [ ] 验证 T034 setup 初始化联动改动的正确性
- [ ] 验证 T035 Grilling 互动式提问改动的正确性

### 验收标准
1. 所有文件语法检查通过
2. 各改动与现有工作流兼容（不破坏已有功能）
