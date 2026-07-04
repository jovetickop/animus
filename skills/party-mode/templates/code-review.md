# 代码审查团模板

> 适用于审查结果争议较大（high 级问题分歧或 implementer 不认可审查结论）时自动触发，也可手动调用。

## 角色

| 序号 | 角色 | Agent | 聚焦问题 |
|------|------|-------|---------|
| 1 | 审查官 | `agents/universal/code-reviewer.md` | 维护原始审查结论，为每个 high 级问题提供证据 |
| 2 | 边界猎手 | `agents/universal/edge-case-hunter.md` | 空值、溢出、并发、资源泄露、重试风暴 |
| 3 | 验收审计官 | `agents/universal/acceptance-auditor.md` | 逐条核对 features.json spec.success 是否满足 |
| 4 | 精简审查官 | `agents/universal/ponytail-reviewer.md` | 是否存在过度工程、可删减抽象、重复代码 |

## 辩论流程

```
1. 陈述
   - 审查官：列出 high 级问题，每项附证据
   - 其他角色：从各自角度确认或质疑
2. 碰撞（≤3 轮）
   - 每人最多 3 次发言
   - 争议项逐条讨论，每条最多 2 轮
   - 目的是收敛到 actionable 结论，不是论输赢
3. 分诊
   每条审查发现按规则分入：
   - [intent_gap] 意图捕获不完整 → 回滚找用户确认
   - [bad_spec] spec 边界不够强 → 修 spec 重做
   - [patch] 局部代码缺陷 → 自动修复
   - [defer] 存量问题 → 记入 deferred-work.md
   - [reject] 误报 → 静默丢弃
4. 结论
   - 确认/调整/驳回的审查项清单
   - 需要 implementer 修复的高优项
```

## 触发条件

| 条件 | 自动触发？ |
|------|-----------|
| 审查有 ≥2 个 high 级分歧 | ✅ 是 |
| implementer 请求重审 | ✅ 是 |
| 用户手动 `/animus-party 代码审查` | ✅ 是 |

## 输出格式

```json
{
  "template": "code-review",
  "original_findings": 12,
  "upheld": 8,
  "overturned": 2,
  "downgraded": 2,
  "action_items": [
    {"id": "F003", "action": "patch", "assignee": "implementer"},
    {"id": "F007", "action": "defer", "file": "deferred-work.md"}
  ]
}
```
