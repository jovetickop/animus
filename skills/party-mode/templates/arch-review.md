# 架构评审团模板

> 适用于跨模块/架构改动，在 dev-full 路径中自动触发，也可手动调用。

## 角色

| 序号 | 角色 | Agent | 聚焦问题 |
|------|------|-------|---------|
| 1 | 架构师 | `agents/<lang>/architect.md` | 方案是否可行？边界是否合理？技术选型是否恰当？ |
| 2 | 审查官 | `agents/universal/code-reviewer.md` | 正确性 bug？安全漏洞？竞态条件？ |
| 3 | 测试官 | `agents/<lang>/test-engineer.md` | 验收标准是否可测？测试策略是否完备？ |
| 4 | 构建师 | `agents/universal/build-doctor.md` | 上线和回滚分别需要几步？依赖风险？CI 影响？ |
| 5 | 规划师 | `agents/universal/feature-planner.md` | 任务拆解是否合理？依赖关系是否正确？ |

## 辩论流程

```
1. 陈述（每人 1 轮）
   - 架构师：陈述方案和关键决策
   - 其他角色：各自角度点评
2. 碰撞（自由辩论，≤2 轮）
   - 每人最多 2 次反驳/补充
   - 聚焦分歧点，不重复共识
3. 收敛
   - 审查官：输出风险清单（high/medium/low）
   - 架构师：根据反馈修正方案
   - 规划师：更新任务拆解
4. 结论
   - 方案版本号（V2/V3...）
   - 最终风险清单
   - 实施顺序建议
```

## 输出格式

```json
{
  "template": "arch-review",
  "conclusion": "架构方案已通过评审",
  "risks": [
    {"level": "high", "desc": "数据库迁移影响现有数据", "owner": "架构师"},
    {"level": "medium", "desc": "第三方库版本兼容性", "owner": "构建师"}
  ],
  "task_updates": [
    "T004 拆分为 T004a 和 T004b",
    "新增 T008 数据库迁移脚本"
  ]
}
```
