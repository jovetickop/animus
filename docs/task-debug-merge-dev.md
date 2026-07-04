# 优化任务：Bug 系统性修复融入 /animus-dev

> 对应路线图：Phase 1 — 核心体验（⑤ Quick Dev 的子任务）
> 解决：`/animus-debug` 独立于 dev 流程，没有任务跟踪和审查门控

---

## 一、更改原因

### 1.1 当前问题

- `/animus-debug` 是独立命令，有自己独立的 4 阶段流程（根因调查→模式分析→假设验证→实施修复）
- 但修复阶段**绕过了 `/animus-dev` 流程**：
  - 不经过 Grilling（没有 spec 记录）
  - 不写 features.json（代码改了什么无法追溯）
  - 不走 review（没有审查门控）
- 用户修 bug 和做功能的体验完全割裂
- 如果调试到一半中断，没有 memlog 事件，无法恢复进度

### 1.2 解决后的效果

- `/animus-debug` 命令直接移除，合并入 `/animus-dev` 成为 debug 专用路径
- Bug 修复有完整的 Grilling → features.json → implement → review 闭环
- 调试过程中的根因分析、修复决策写入 memlog
- 用户不需要区分"我在修 bug 还是做功能"——都是 `/animus-dev`

---

## 二、更改方案

### 2.1 路由变更

`/animus-dev` 从四路变为**五路**：

```
用户输入 → AI 检测意图类型
  ├── bug fix（报错/异常行为/回归）→ debug-path（3 问调试专用）
  ├── 1-2 文件 / 小改动 → fast-path（1 句确认）
  ├── 3-10 文件 / 新增功能 → light-path（3 问）
  └── 跨模块 / 架构改动 → full-path（7 问 + 可选脑暴）
```

### 2.2 Bug 检测规则

AI 根据用户输入自动判断是否为 bug（触发 debug-path）：

| 信号 | 示例 | 判定 |
|------|------|------|
| 明确提及 bug/异常 | "有个 bug""不 work""崩溃" | ✅ bug |
| 描述预期 vs 实际差异 | "按钮点了没反应""应该显示 3 条但只显示 1 条" | ✅ bug |
| 回归场景 | "上次更新后就不能用了" | ✅ bug |
| 描述缺失/错误行为 | "数据没有保存""日志一直在报错" | ✅ bug |

### 2.3 Debug-path 专用 Grilling（3 问）

| # | 问题 | 说明 | 产出 |
|---|------|------|------|
| 1 | **复现步骤与影响范围** | "什么操作触发的？预期行为 vs 实际行为？影响哪些用户？" | 复现步骤 + 严重度评估 |
| 2 | **根因初步推断** | "根据症状，你怀疑是哪层的问题？有没有日志/堆栈信息？" | 嫌疑模块 + 证据链 |
| 3 | **修复策略与副作用评估** | "修复会影响哪些已有功能？需要加什么测试防止回归？" | 修复范围 + 回归测试点 |

### 2.4 Debug-path 的 features.json 写入

```
features.json:
  T004:
    title: "修复 PDF 导出崩溃（空指针）"
    status: in_progress
    type: bugfix
    severity: high                # critical / high / medium / low
    spec:
      why: "导出空报告时 crash，影响所有离线用户"
      repro_steps: ["打开空报告", "点击导出 PDF", "应用 crash"]
      root_cause: "report->pageCount() 为 0 时 pdf_engine 未初始化"
      constraints: ["不影响正常导出", "不改变 API 签名"]
      non_goals: ["不重构 PDF 模块"]
      success: "空报告导出时不 crash，显示'无内容可导出'提示"
    verify_command: "python test_pdf_export.py --empty"
```

### 2.5 Debug-path 流程

```
/animus-dev <bug描述>
  → AI 检测为 bug
  → 路径确认："检测到 bug，使用 debug-path（系统性修复流程）"
  → 3 问 Grilling（复现→根因→修复策略）
  → 写入 features.json（type=bugfix + severity + repro_steps）
  → implementer 实施修复
  → 按 spec.success 验证（包含 verify_command）
  → 4 agent 审查（code-reviewer + edge-case-hunter + acceptance-auditor + ponytail-reviewer）
  → passed → 写入 memlog（决策事件记录根因和修复方案）
```

对比原 `/animus-debug` 的 4 阶段（根因调查→模式分析→假设验证→实施修复），**逻辑内容不变**，只是换成了 dev 流程的框架（Grilling + features.json + review）。

### 2.6 改动文件

| 文件 | 改动 |
|------|------|
| **删除** `commands/animus-debug.md` | 功能合并入 `/animus-dev` |
| 修改 `commands/animus-dev.md` | 五路路由 + bug 检测规则 + debug-path Grilling |
| 修改 `plugin.json` | 删除 `animus-debug` 注册 |
| 修改 `commands/animus-help.md` | 移除 `/animus-debug` 帮助条目 |
| 修改 `docs/agent-index.md` | 移除 debug 相关 agent 引用（如有） |

### 2.7 不改动的部分

- 系统性修复的**方法论本身**（`skills/systematic-debugging/`）保留，作为 implementer 修复 bug 时的参考知识
- `agents/universal/build-doctor.md` 保留（构建相关的诊断仍由其处理）

---

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 无影响——只是路由逻辑多一个分支 |
| 兼容性 | `/animus-debug` 直接删除，用户改用 `/animus-dev`，功能完全覆盖 |
| 降级 | AI 误判 bug vs feature 时，用户可用 `--fast` 或 `--full` 手动覆盖 |
| 风险 | 修复方案变更（比如从补丁改为重写）时需重新走 debug-path 或切换到 full-path |

## 四、验证方法

1. 输入"PDF 导出崩溃" → 确认走 debug-path，3 问 Grilling
2. 确认 features.json 有 `type: bugfix`、`severity`、`repro_steps`、`root_cause` 字段
3. 修复后走完整 review → 确认 passed/passed
4. 输入"加个按钮" → 确认不走 debug-path，正常选 fast/light/full
5. 确认 `/animus-debug` 已移除 → 访问返回"命令未找到"
6. 确认 memlog 中记录修复根因和方案的决策事件
