---
name: animus-dev
search_phrases: ["/dev", "develop", "implement", "代码", "开发", "bug", "debug", "修复", "feature"]
description: 统一开发入口（四路路由：debug/fast/light/full）
---

# /animus-dev — 统一开发入口

## 功能

一个入口处理所有开发场景：从改个颜色到架构设计，从修 bug 到加新功能。

## 路由概览

| 路径 | 触发条件 | 流程 |
|------|---------|------|
| **debug** | bug 报告 / 异常 / 回归 | 3 问诊断 → features.json → implement → 4 agent review |
| **fast** | 1-2 文件 / 小改动 / 配置修改 | 1 句确认 → 创建 task → features.json → implement → review |
| **light** | 3-10 文件 / 新增功能 | 3 问 → 拆任务 → features.json → implement → review |
| **full** | 跨模块 / 架构级改动 | 7 问 + 可选脑暴 → 拆任务队列 → features.json → implement → review |

## 路径选择逻辑

1. 检测 memlog 是否有事件 → 有则自动重建 features.json，输出「检测到上次进度，已恢复」
2. 检测 features.json 是否有 in_progress 任务 → 有则直接继续实施
3. 根据用户输入自动判断意图类型，选路
4. 输出「检测到 XX，将使用 XX 路径」，等待用户确认
5. 用户确认后进入对应路径的 Grilling 流程
6. 所有路径结束后写入 features.json，走 implement → review

> 配置文件 config.toml 中 `dev.autonomous = true` 时跳过第 4 步确认。

## 各路径详细流程

### debug 路径 — bug 修复

适用于：bug 报告、异常、回归、崩溃

**第 1 步：3 问定位**

1. 复现步骤与影响范围 — 什么操作触发的？预期 vs 实际？影响哪些用户？
2. 根因初步推断 — 根据症状怀疑哪层的问题？有日志或堆栈吗？
3. 修复策略与副作用评估 — 修复会影响哪些已有功能？需要加什么测试？

**第 2 步：无法复现？走穷举分析**

```
无法稳定复现
  ├── 日志狩猎 — 检查应用/系统日志，找异常堆栈、panic、超时记录
  ├── 路径穷举 — 遍历所有分支路径，标出竞态条件、超时窗口、未处理边界
  ├── 埋点策略 — 在可疑路径加日志/计数器，输出到独立文件
  └── 环境差异 — 对比用户环境 vs 开发环境的版本、配置、资源限制
```

**第 3 步：创建 bugfix 任务写入 features.json**

```json
{
  "T004": {
    "title": "PDF 导出崩溃",
    "status": "in_progress",
    "spec": {
      "why": "用户导出 PDF 时程序闪退",
      "repro_steps": "1. 打开任意文档 2. 文件 → 导出为 PDF 3. 程序无响应",
      "root_cause": "推测 QPrinter 初始化时缺少打印机驱动检查",
      "success": "导出 PDF 正常完成，不崩溃"
    }
  }
}
```

**第 4 步：implement → review**（审查分诊时标记 patch/defer/reject）

---

### fast 路径 — 小改动

适用于：改动明确、影响范围小、1-2 文件

**确认问题：**

```
检测到变更范围：1 个文件，按钮颜色值修改
→ 1 句确认：是否将按钮文字颜色从 #333 改为 #FFF？
```

用户确认后直接走 implement → review。

---

### light 路径 — 新增功能

适用于：新增功能、3-10 文件、中等复杂度

**第 1 步：3 问明确需求**

1. 这个功能做什么的？解决了什么问题？
2. 依赖哪些现有模块/接口/数据？
3. 怎么验证做对了？验收步骤是什么？

**第 2 步：拆任务 → 写入 features.json → implement → review**

---

### full 路径 — 架构级改动

适用于：跨模块重构、架构变更、复杂功能

**第 1 步：7 问完整 Grilling**

1. **验收标准** — 从用户视角描述，完成后怎么验证
2. **前置依赖** — 已有模块、数据表、第三方服务
3. **异常流程** — 错误提示策略、回滚、降级
4. **性能/安全** — 加密、限流、超时、并发量级
5. **架构约束** — 分层、设计模式、技术栈限制
6. **风险** — 并发竞争、边界条件、第三方依赖
7. **测试策略** — 单元测试、集成测试、E2E

**第 2 步：可选脑暴**

用户描述模糊时（"我想做 X 但不知道从哪开始"），集成以下技法：

| 用户说... | 自动启用技法 |
|-----------|------------|
| "我想做 X 但不知道从哪开始" | PRFAQ——先写假想发布公告 |
| "这个功能有没有更简单的方式" | 第一性原理——拆到基本元素再重建 |
| "这个功能还能怎么优化" | SCAMPER——七问检查法 |
| "有什么风险我没想到" | 反方案——想象怎么把功能搞砸，再反向修复 |

**第 3 步：拆任务队列 → 写入 features.json → 逐任务 implement → review**

---

## 强制参数

| 参数 | 效果 |
|------|------|
| `--debug` | 强制走 debug 路径（3 问调试专用），不自动检测 |
| `--fast` | 强制走 fast 路径（1 句确认），不自动检测 |
| `--full` | 强制走 full 路径（7 问完全 Grilling），不自动检测 |

无参数时 AI 自动检测。

## 任务门控

所有路径都写 features.json，agent 没有 in_progress 任务不能写代码。
配合 PreToolUse hook（write-gate）做硬拦截。详见 `docs/task-09-write-gate-hook.md`。

## deferred-work 机制

review 中发现的存量问题标记为 `defer`，记入 `.claude/animus/deferred-work.md`：
- 不混入当前修复流程，不阻塞主线
- 下次 `/animus-dev` 启动时自动读取，作为参考但不强制
- 格式：日期 + 来源任务 + 路径 + 描述

## 并行任务

如果需同时改动多个独立模块（如前后端同时改），自动拆分为并行 group：
- 每个 group 独立走路由流程（各自 features.json 任务）
- implement 阶段独立实施
- review 阶段先逐一审查，再合并审查确认无 group 间冲突
- 全部 group 完成后统一更新主 features.json

## 参考

详见 `docs/task-05-QuickDev.md` 和 `docs/task-debug-merge-dev.md`。
