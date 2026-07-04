---
command: /animus-archive
description: 归档当前迭代，打包所有状态文件到 archive/iteration-N-<name>/，清空并开始新迭代
---

# /animus-archive 归档迭代

## 功能

将当前 `.claude/animus/` 中的运行时状态打包归档，清空当前状态，开始新迭代。

## 流程

1. **询问迭代名称**：让用户输入本次迭代的自定义名称
2. **检查未完成任务**：读取 features.json，检查是否有 pending/in_progress 的任务
   - 如果有，使用 `AskUserQuestion` 询问用户：
     - **继续完成** → 不归档，返回继续工作
     - **丢弃未完成任务** → 继续归档流程
3. **确认归档**：列出当前任务统计（通过/失败/待处理数量），确认是否继续
4. **执行归档**：运行 `python scripts/archive-iteration.py --project-dir . --name "<名称>"`
5. **生成总结**：自动写入 iteration-summary.md（功能列表、代码统计、起止时间）
6. **清空当前状态**：features.json 重置为空任务数组
6. **输出结果**：显示归档路径和新迭代编号
