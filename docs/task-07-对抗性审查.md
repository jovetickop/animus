# 优化任务 ⑦：对抗性审查系统

> 对应路线图：Phase 2 — 能力增强（重编号后对应 ⑦）
> 解决：单 agent 审查有盲点，缺少过度工程检查

---

## 一、更改原因

### 1.1 当前问题

- `/animus-review` 调用单一 `code-reviewer` agent，一个人看总有盲点
- 边界条件（空值、溢出、并发）经常被跳过
- 验收条件（features.json 里的 spec）不自动验证
- 没有"代码是否过度工程"的检查
- implementer 开发时缺少"写最少代码"的约束

### 1.2 解决后的效果

- 4 个 agent 平行审查，覆盖正确性/边界/验收/精简
- high 级问题阻塞，low 自动通过，medium 人工确认
- implementer 开发时参考 ponytail 原则，少写无用代码
- 审查结果汇总报告，冲突处可追溯

---

## 二、更改方案

### 2.1 4 个审查 agent

| # | Agent | 角色 | 重点检查项 | 输出示例 |
|---|-------|------|-----------|---------|
| 1 | **code-reviewer** | 审查官 (Review) | 正确性 bug、安全漏洞、竞态条件、空指针、类型错误 | `src/main.cpp:42: HIGH 空指针解引用` |
| 2 | **edge-case-hunter** | 边界猎手 | 空值、溢出、并发、资源泄露、超时、零值、负数 | `src/calc.cpp:15: MEDIUM 整数溢出风险` |
| 3 | **acceptance-auditor** | 验收审计官 | 逐条核对 features.json spec.success 是否满足 | `T005: PASS 导出路径可选` |
| 4 | **ponytail-reviewer** | 精简审查官 | 过度工程、可删减代码、不必要的抽象、死灵活度 | `src/parser.cpp:88: LOW 接口多一层包装` |

### 2.2 审查触发时机

**自动触发：** 每次 `/animus-dev` 完成实施后，自动启动 4 agent 平行审查。

**手动触发：** `/animus-review` 命令保留，用户可随时重审或单独调用。

### 2.3 门控规则

| 审查结果 | 门控行为 |
|---------|---------|
| 全部 agent 无 high 级问题 | ✅ 允许 passed |
| 有 high 级问题 | ❌ 阻塞，必须修复 |
| 有 medium 问题 | ⚠️ 标记待人工确认，不阻塞 |
| 有 low 问题 | ✅ 自动通过，计入报告 |

### 2.4 并行执行模式

```
/animus-dev 实施完成
  → 并行启动 4 个 agent（不等待彼此）
       ├── code-reviewer → 报告 CR.md
       ├── edge-case-hunter → 报告 EC.md
       ├── acceptance-auditor → 报告 AA.md
       └── ponytail-reviewer → 报告 PR.md
  → 等待全部完成（或超时）
  → 合并 4 份报告
  → 按门控规则裁决
  → 更新 features.json 对应任务状态
```

### 2.5 循环回退机制

审查不通过时，退回 implementer 修复后重新审查，最多 **3 轮**：

```
第 1 轮审查 → 发现 high 问题 → 退回 implementer 修复
     ↓
第 2 轮审查 → 仍有 high 问题 → 退回 implementer 修复
     ↓
第 3 轮审查 → 仍有 high 问题 → ❌ 审查终止，报错
```

**超时降级：** 严格模式——任何 agent 失败/超时 → 自动重试最多 **3 次** → 仍失败 → 审查终止报错。

**回退流程：**
1. 审查发现有 high 级问题，生成审查报告
2. 自动退回 implementer，implementer 根据报告修复
3. 重新启动 4 agent 平行审查
4. 重复步骤 1-3，直到无 high 问题或达到 3 轮上限
5. 3 轮后仍有 high 问题 → 审查终止，人工介入

### 2.6 报告合并格式

```markdown
# 审查报告：T005 PDF 导出

## 汇总
| Agent | 结论 | High | Medium | Low |
|-------|------|------|--------|-----|
| code-reviewer | PASS | 0 | 1 | 2 |
| edge-case-hunter | PASS | 0 | 0 | 1 |
| acceptance-auditor | PASS | — | — | — |
| ponytail-reviewer | PASS | 0 | 1 | 0 |

## 待处理问题
- **MEDIUM** code-reviewer: src/pdf_export.cpp:42 未检查写入权限
- **MEDIUM** ponytail-reviewer: src/pdf_export.cpp:88 导出的 PrintSettings 类可以简化

## 裁决
✅ 无 high 问题 → 通过
⚠️ medium 问题已标记，建议修复后重审
```

### 2.7 implementer ponytail 原则

修改 implementer agent 指令，追加：

```
## 开发原则（ponytail）
- 用标准库替代自定义代码
- 不添加可能用不到的抽象层
- 不提前做"将来可能需要"的扩展点
- 一个功能一个实现方式，不提供多种方案
- 能删则删，能简则简
```

### 2.8 改动文件

| 文件 | 改动 |
|------|------|
| 新建 `agents/universal/edge-case-hunter.md` | 新 agent：边界审查 |
| 新建 `agents/universal/acceptance-auditor.md` | 新 agent：验收审计 |
| 新建 `agents/universal/ponytail-reviewer.md` | 新 agent：精简审查（参考 ponytail-review 内容） |
| 修改 `commands/animus-review.md` | 并行调用 4 agent + 结果聚合 + 循环回退逻辑 + 超时降级 |
| 修改 implementer agent | 追加 ponytail 开发原则 |
| 修改 `scripts/validate-features.py` | 门控逻辑更新 + 循环回退计数 + 3 轮上限 |
| `.claude/animus/config.toml` | 追加 `[review]`、`[ponytail]` 配置段 |

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 最多 4 agent × 3 轮 = 12 次审查调用，耗时增加但仅在 high 问题时触发 |
| 兼容性 | `/animus-review` 接口不变，输出格式向后兼容 |
| 降级 | 超时/失败 → 自动重试 3 次 → 仍失败则终止报错；单 agent 失败不影响其他 agent 结果 |

## 四、验证方法

1. 提交一个有故意 bug 的代码 → 确认 code-reviewer 报 high
2. 提交一个缺少边界检查的代码 → 确认 edge-case-hunter 报 medium
3. 提交一个不满足 features.json spec 的代码 → 确认 acceptance-auditor 报 failed
4. 提交一个过度抽象的代码 → 确认 ponytail-reviewer 报 medium
5. 确认 high 阻塞时 features.json 状态未改为 passed
6. 确认 4 个 agent 并行启动，耗时约等于最慢的一个
7. 连续 3 轮审查失败 → 确认审查终止报错，不无限循环
