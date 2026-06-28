---
command: /harness-code-archive
description: 归档当前迭代，打包所有状态文件到 archive/iteration-N-<name>/，清空并开始新迭代
---

# /harness-code-archive 归档迭代

## 功能

将当前 `.claude/harness-cc/` 中的运行时状态打包归档，清空当前状态，开始新迭代。

## 流程

1. **询问迭代名称**：让用户输入本次迭代的自定义名称
2. **确认归档**：列出当前任务统计（通过/失败/待处理数量），确认是否继续
3. **执行归档**：运行 `python scripts/archive-iteration.py --project-dir . --name "<名称>"`
4. **生成总结**：自动写入 iteration-summary.md（功能列表、代码统计、起止时间）
5. **清空当前状态**：features.json 重置为空任务数组
6. **输出结果**：显示归档路径和新迭代编号
