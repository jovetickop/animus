---
type: reference
audience: regular-user
---

# 命令参考

> Animus 的 7 个斜杠命令 — 用途、用法、配置说明。

---

## 命令一览

| 命令 | 用途 | 典型场景 |
|------|------|---------|
| `/animus-init` | 项目初始化 | 首次在新项目中使用 animus |
| `/animus-dev` | 统一开发入口 | 开始一个开发任务 |
| `/animus-review` | 代码审查 | 任务完成后的质量门控审查 |
| `/animus-party` | 辩论模式 | 架构评审或代码审查的多角度讨论 |
| `/animus-status` | 状态看板 | 查看当前任务进度 |
| `/animus-help` | 帮助导航 | 不确定下一步做什么 |
| `/animus-archive` | 迭代归档 | 完成一轮迭代后归档 |

---

## `/animus-init` — 项目初始化

**原理：** 检测目标项目的技术栈类型，创建 `.claude/animus/` 运行时目录。

**检测规则：**

| 项目文件 | 识别类型 |
|---------|---------|
| `CMakeLists.txt` + `find_package(Qt)` | cpp-qt |
| `CMakeLists.txt`（无 Qt） | cpp-cmake |
| `Cargo.toml` | rust |
| `go.mod` | go |
| `package.json` | node |
| `pyproject.toml` 或 `requirements.txt` | python |
| 以上均无 | generic |

**执行内容：**
1. 检测项目根目录
2. 按文件列表判定语言栈
3. 根目录未识别时扫描一级子目录
4. 创建 `.claude/animus/` 目录
5. 写入默认 `config.toml`
6. 生成初始 `features.json`

---

## `/animus-dev` — 统一开发入口

**原理：** 根据用户输入的意图描述，AI 自动判断改动范围和类型，选择最合适的开发路径。

**四路自动分流：**

| 路径 | 触发条件 | 流程 | 示例 |
|------|---------|------|------|
| debug | bug 报告/异常 | 3 问 → features.json → implement → review | "PDF 导出崩溃" |
| fast | 1-2 文件/小改动 | 1 句确认 → features.json → implement → review | "改按钮颜色" |
| light | 3-10 文件/新增 | 3 问 → features.json → 拆任务 → implement → review | "加导出功能" |
| full | 跨模块/架构改动 | 7 问 + 可选脑暴 → 拆任务 → implement → review | "重构数据层" |

**自动恢复：** 启动时检测 memlog/ 有事件 → 自动执行 `python animus-engine.py rebuild` 恢复 features.json。

**配置：**
```toml
[dev]
default_path = "auto"
autonomous = false
```

---

## `/animus-review` — 代码审查

**原理：** 4 agent 并行审查，从正确性、边界条件、验收标准、精简度四个维度审查代码。

**审查维度：**

| Agent | 重点检查项 |
|-------|-----------|
| 审查官 (Review) | 正确性 bug、安全漏洞、竞态条件 |
| 边界猎手 (Edge Case Hunter) | 空值、溢出、并发、资源泄露 |
| 验收审计官 (Acceptance Auditor) | 逐条核对 features.json spec.success |
| 精简审查官 (Ponytail Reviewer) | 过度工程、可删减抽象 |

**门控规则：**

| 审查结果 | 处理 |
|---------|------|
| 无 high 级问题 | ✅ 允许 passed |
| 有 high 级问题 | ❌ 阻塞，退回 implementer |
| 有 medium 问题 | ⚠️ 标记人工确认，不阻塞 |
| 有 low 问题 | ✅ 自动通过 |

**循环回退：** 最多 3 轮修复-审查循环，超限人工介入。

**配置：**
```toml
[review]
strictness = "normal"
max_findings = 20
```

---

## `/animus-party` — 辩论模式

**原理：** 多 agent 并行辩论，从不同角度碰撞观点。

**模板：**

| 模板 | 参与角色 | 人数 |
|------|---------|------|
| `arch-review` | 架构师+审查官+测试官+构建师+规划师 | 5 |
| `code-review` | 审查官+边界猎手+验收审计官+精简审查官 | 4 |

**运行模式：** session / subagent（推荐）/ auto / agent-team

---

## `/animus-status` — 状态看板

**原理：** 读取 features.json，统计任务状态分布，输出推荐下一步。

**输出结构：**
```
统计概览 → 任务明细 → 推荐下一步
```

**推荐规则：**
1. 有 in_progress → 继续实施
2. 有 failed → 修复重试
3. 有 pending → 开始新任务
4. 有 passed 未完成 → 需要审查
5. 全部完成 → 归档迭代

---

## `/animus-help` — 帮助导航

**原理：** 读取 `.claude/animus/` 目录状态，根据进度推荐最合适的命令。

| 当前状态 | 推荐命令 |
|---------|---------|
| 无 features.json | `/animus-init` |
| features.json 无任务 | `/animus-dev` |
| 有进行中任务 | `/animus-dev` 继续 |
| 有完成未审查 | `/animus-review` |
| 全部完成 | `/animus-archive` |

---

## `/animus-archive` — 迭代归档

**原理：** 将当前迭代完整状态打包到 `archive/iter-xxx/`，清空数据开始新迭代。

**归档内容：**

| 内容 | 去向 |
|------|------|
| memlog 所有事件 | 复制到归档 memlog/ |
| features.json | 复制到归档目录 |
| iteration-summary.md | 自动生成到归档目录 |
| config.toml | 保留不变 |

**命令选项：**
```
/animus-archive                           # 交互式：输入名称
/animus-archive --name "迭代 3-UI重构"     # 直接归档
```

---

## 引擎 CLI

除斜杠命令外，引擎脚本也可直接调用：

```bash
python scripts/animus-engine.py status              # 显示状态
python scripts/animus-engine.py transition <id> <to> # 状态流转
python scripts/animus-engine.py validate            # 校验 features.json
python scripts/animus-engine.py validate --plugin   # 校验插件完整性
python scripts/animus-engine.py archive             # 归档
python scripts/animus-engine.py rebuild             # 从 memlog 重建
```
