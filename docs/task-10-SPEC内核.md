# 优化任务 ⑩：SPEC 内核 + features.json 合并

> 对应路线图：Phase 3 — 深度建设（重编号后对应 ⑩）
> 解决：任务描述质量参差不齐，task_plan.md 和 features.json 两份不一致

---

## 一、更改原因

### 1.1 当前问题

- features.json 中任务描述自由填写，质量参差不齐
- task_plan.md 和 features.json 两者并存，可能不一致
- 没有结构化的"为什么做、做什么、不做什么"
- acceptance-auditor 无法自动验证任务是否完成

### 1.2 解决后的效果

- 每个任务有 5 字段 spec（why/capabilities/constraints/non_goals/success）
- 移除 task_plan.md，全部并入 features.json
- acceptance-auditor 直接读 spec.success 自动验证
- Grilling 对话写入 memlog，重启后可恢复完整上下文

---

## 二、更改方案

### 2.1 features.json 新的 schema

```json
{
  "metadata": {
    "project": "ty-qt-ai-plugin",
    "version": "1.3.0",
    "updated": "2026-07-04T12:00:00+08:00"
  },
  "tasks": {
    "T004": {
      "title": "修按钮颜色",
      "status": "in_progress",
      "created": "2026-07-04T10:00:00+08:00",
      "spec": {
        "why": "按钮和背景色太接近看不清",
        "capabilities": ["修改按钮文本颜色值"],
        "constraints": ["只改动 .qml 文件，不改逻辑"],
        "non_goals": ["不修改按钮大小和位置"],
        "success": "按钮文字在白色背景下清晰可见"
      }
    },
    "T005": {
      "title": "添加 PDF 导出",
      "status": "pending",
      "created": "2026-07-04T11:00:00+08:00",
      "spec": {
        "why": "客户需要在离线状态下分享报告",
        "capabilities": [
          "选择导出范围（当前页/全部页）",
          "生成 PDF 文件",
          "选择保存路径"
        ],
        "constraints": [
          "依赖 Qt PDF 模块",
          "导出时间不超过 5 秒",
          "文件大小不超过 50MB"
        ],
        "non_goals": [
          "不处理加密 PDF",
          "不支持批量导出",
          "不处理 PDF/A 格式"
        ],
        "success": "用户选定 3 页报告后 3 秒内生成可打开的 PDF"
      }
    }
  }
}
```

### 2.2 spec 字段说明

| 字段 | 必填 | 含义 | 示例 |
|------|------|------|------|
| `why` | 是 | 为什么要做 | "客户离线需要分享报告" |
| `capabilities` | 否 | 做什么（功能列表） | "选择导出范围、生成 PDF" |
| `constraints` | 否 | 约束条件 | "依赖 Qt PDF、不超过 5 秒" |
| `non_goals` | 否 | 明确不做什么 | "不支持批量导出" |
| `success` | 是 | 怎么算做完了 | "3 秒内生成可打开的 PDF" |

**`why` 和 `success` 是所有路径都需要的**，其他三个字段按 Grilling 深度决定填充度。

### 2.3 Grilling 深度与 spec 质量的对应

| 路径 | 提问数 | why | capabilities | constraints | non_goals | success |
|------|--------|-----|-------------|------------|-----------|---------|
| fast | 1 问 | 用户确认 | AI 推断 | AI 推断 | AI 推断 | 用户确认 |
| light | 3 问 | 用户确认 | 用户提及 | AI 推断 | AI 推断 | 用户确认 |
| full | 7 问 | 用户确认 | 用户确认 | 用户确认 | 用户确认 | 用户确认 |

空字段在 JSON 中为 `[]` 或 `null`，不影响 schema 完整性。

### 2.4 移除 task_plan.md

`task_plan.md` 的内容全部归入 features.json 的 spec 字段。

原有的 task_plan.md 文件在迁移后删除。如果用户有遗留的 task_plan.md，可以执行迁移脚本读取内容写入 features.json 的 spec 字段，然后删除文件。

### 2.5 memlog 记录 Grilling 上下文

每次 Grilling 对话的关键内容写入 memlog `decision` 事件：

```markdown
---
type: decision
timestamp: 2026-07-04T10:05:00+08:00
task_id: T005
phase: grilling
---

# Grilling 上下文：T005 PDF 导出

## 用户原话
"客户每次导出报告都要在线，他们经常在飞机上用"

## 功能范围确认
- 用户确认只需 PDF 格式
- 不需要 Word/Excel 导出
- 每份报告不超过 50MB

## 排除方案
- wkhtmltopdf → 排除，额外装工具
- libharu → 排除，C API 太原始
- Qt PDF → 选中，零额外依赖

## 关键决策
- 异步生成，不阻塞 UI
- 进度条反馈
- 生成完成前不允许关闭窗口
```

### 2.6 4 条核心规范法则

被 `scripts/validate-features.py` 自动校验：

| # | 法则 | 要求说明 | 校验方式 |
|---|------|---------|---------|
| 1 | **why 必填** | 每个任务必须有明确的业务原因，不能为空或"同上" | `spec.why` 非空字符串 |
| 2 | **success 必填且可验证** | success 必须是可观测、可测试的陈述，不能是"完成就好" | `spec.success` 非空且包含可观测指标（如时间、数量、状态） |
| 3 | **constraints 必须实际约束** | 不能是"用良好的代码风格"这种非约束，必须是具体限制条件 | `spec.constraints` 中每个元素必须有具体值（版本号、时间、大小等） |
| 4 | **non_goals 必须明确** | 明确说"不做"什么，不能留空或写"暂无" | `spec.non_goals` 非空数组，每个元素以"不"开头 |

违反法则时 validate-features.py 抛出 WARNING（不阻塞），但 full-path 必须全部满足。

### 2.7 改动文件

| 文件 | 改动 |
|------|------|
| `commands/animus-dev.md` | Grilling 逻辑自动填充 spec 5 字段 |
| `.claude/animus/features.json` | schema 扩 spec 字段 |
| 移除 `task_plan.md` | 功能归入 features.json |
| `scripts/validate-features.py` | 校验 spec 字段结构 |
| `agents/universal/acceptance-auditor.md` | 按 spec.success 逐条验证 |

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 无影响——spec 校验仅在任务创建/更新时执行 |
| 兼容性 | 旧 features.json 缺少 spec 字段时降级为无 spec 状态，不报错 |
| 降级 | 4 条法则校验不通过时仅输出 WARNING，不阻塞任务创建 |

## 四、验证方法

1. 执行 `/animus-dev 修按钮颜色` → 确认 features.json 有 spec 5 字段
2. 执行 `/animus-dev --full 加 PDF 导出` → 确认 7 问后 spec 详尽
3. 确认 `task_plan.md` 不再生成
4. 确认 acceptance-auditor 能读 spec.success 做验收
5. 确认 memlog 中有对应 Grilling 上下文事件
6. 故意写空 why 字段 → 确认 validate-features.py 报 WARNING
7. 故意写不可验证的 success → 确认法则 2 触发
