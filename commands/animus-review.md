---
description: 执行通用检查 + 按项目类型的专项验收检查
---

# /animus-review — 代码审查

## 功能

并行启动 4 个审查 agent 进行多维度审查，结果汇总后按严重度分级裁决。

## 4 agent 并行审查

| Agent | 角色 | 重点检查项 |
|-------|------|-----------|
| **code-reviewer** | 审查官 | 正确性 bug、安全漏洞、竞态条件、空指针、类型错误 |
| **edge-case-hunter** | 边界猎手 | 空值、溢出、并发、资源泄露、超时、零值、未处理分支 |
| **acceptance-auditor** | 验收审计官 | 逐条核对 features.json spec.success 是否满足 |
| **ponytail-reviewer** | 精简审查官 | 过度工程、可删减抽象、重复代码 |

## 门控规则

| 审查结果 | 处理 |
|---------|------|
| 全部 agent 无 high 级问题 | ✅ 允许 passed |
| 有 high 级问题 | ❌ 阻塞，退回 implementer 修复 |
| 有 medium 问题 | ⚠️ 标记待人工确认，不阻塞 |
| 有 low 问题 | ✅ 自动通过，计入报告 |

## 5 类分诊

每条审查发现按以下 5 类处理：

| 标签 | 定义 | 处理方式 |
|------|------|---------|
| **intent_gap** | 意图捕获不完整导致的 bug（不是代码问题） | 回滚 → 找用户确认意图 |
| **bad_spec** | spec 边界不够强，实现走偏 | 回滚 → 修 spec → 重新实现 |
| **patch** | 局部代码缺陷 | 直接自动修复 |
| **defer** | 存量问题，不是本次改动引入的 | 记入 `deferred-work.md`，不打断主线 |
| **reject** | 误报、吹毛求疵 | 静默丢弃 |

**处理顺序：** 先处理 intent_gap 和 bad_spec（代码会被重推），再处理 patch。defer 和 reject 不阻塞流程。

## 循环回退

审查不通过 → 退回 implementer 修复 → 重新审查，最多 **3 轮**。超限后审查终止，报错人工介入。

## 超时降级

任何 agent 超时 → 自动重试最多 3 次 → 仍失败 → 审查终止。

## 报告格式

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
- [patch] code-reviewer: src/pdf_export.cpp:42 未检查写入权限
- [defer] ponytail-reviewer: src/legacy_parser.cpp:120 已有代码坏味道（存量）

## 裁决
✅ 无 high 问题 → 通过
```

## deferred-work 记录

标记为 defer 的问题记入 `.claude/animus/deferred-work.md`：

```markdown
## 2026-07-04 — T005 审查
- [ ] `src/legacy_parser.cpp:120` 缺乏输入长度检查
- [ ] `src/database.cpp:45` 连接池没有超时机制
```

## 语言专项检查

- C++/Qt：智能指针、QObject 生命周期、信号槽连接
- Rust：所有权、借用检查、unsafe 代码
- Go：goroutine 泄漏、error 处理
- Node：回调地狱、内存泄漏
- Python：类型注解、异常处理

辅助验证脚本：
- `${CLAUDE_PLUGIN_ROOT}/commands/validate-features.ps1` — 验证 features.json 结构
- `${CLAUDE_PLUGIN_ROOT}/commands/check-consistency.ps1` — 检查状态一致性

### 并行任务审查
完成并行任务后，先逐一审查每个 group 的变更，
再整体审查合并后的全量差异，确认无 group 间冲突。
