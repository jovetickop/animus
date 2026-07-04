# Feature Detail

## T024 - 差距分析框架
状态: passed | 优先级: P0 | 依赖: 无

### 子功能
- [x] Layer 0: feature-detail.md 文件
- [x] Layer 1: CLAUDE.md Rule（Gap Analysis + Sync Docs + Use RTK）
- [x] Layer 2: feature-planner Step 0（差距分析）
- [x] Layer 3: requirements-tracking.md 规则文件
- [x] Layer 4: gap-analysis.py 脚本

### 验收标准
1. CLAUDE.md 包含两条新 Rule
2. feature-planner.md 有 Step 0
3. rules/universal/requirements-tracking.md 存在
4. scripts/gap-analysis.py 存在且可运行

---

## T025 - Handoff
状态: pending | 优先级: P0 | 依赖: T024

### 子功能
- [ ] /animus-handoff 命令
- [ ] /animus-continue 命令
- [ ] handoff.json 格式定义
- [ ] session-catchup.py 增强
- [ ] plugin.json 注册命令

### 验收标准
1. /animus-handoff 生成 handoff.json
2. /animus-continue 读取并恢复上下文
3. 加载后标记 status=loaded 防重复

---

## T026 - Domain Lexicon
状态: pending | 优先级: P0 | 依赖: T024

### 子功能
- [ ] domain-lexicon.md 模板
- [ ] feature-planner 术语提取指令
- [ ] task-implementer 术语追加指令

---

## T027 - ADR
状态: pending | 优先级: P0 | 依赖: T024

### 子功能
- [ ] ADR 模板 + 目录
- [ ] task-implementer-core.md ADR 指令
- [ ] 7 个 architect agent ADR 指令

---

## T028 - Parallel Design
状态: pending | 优先级: P1 | 依赖: 无

---

## T029 - 自动更新插件
状态: pending | 优先级: P0 | 依赖: 无

---

## T030 - Grillme-with-doc
状态: pending | 优先级: P0 | 依赖: T024

---

## T031 - 迭代归档
状态: pending | 优先级: P0 | 依赖: 无

---

## T032 - verify_config 迁移
状态: pending | 优先级: P0 | 依赖: 无
