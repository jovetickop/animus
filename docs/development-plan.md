# Animus 开发计划

> 基于 `bmad-optimization-roadmap.md` 生成，附带严格的验证门控。
> 总计 4 个 Phase，10 周工期。

---

## 验证门控总则

每个 Sprint 的输出必须通过以下门控才能进入下一 Sprint：

| 门控级别 | 含义 | 不通过时的行为 |
|---------|------|-------------|
| **◎ HARD** | 必须通过，否则阻塞 | 禁止进入下一 Sprint，必须修复后重过 |
| **○ SOFT** | 应该通过，中度问题可延期 | 记录为已知问题，下个 Sprint 修复 |
| **△ INFO** | 参考性检查 | 不阻塞，仅记录 |

所有 HARD 门控的验证必须可复现、可自动化。

---

## Phase 0：基础设施（Sprint 0.1 – 0.2）

**工期：** 第 1-2 周
**前置依赖：** 无
**产出：** `config.toml` 三层配置体系 + `animus-engine.py` 统一 CLI

---

### Sprint 0.1：三层定制与团队配置（⑨）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 0.1.1 | 创建 `.claude/animus/config.toml` 默认配置 | `config.toml`（新建） | 文件存在；所有配置段（dev/review/gates/ponytail/party_mode）可解析 |
| 0.1.2 | 创建 `.claude/animus/config.user.toml` | `config.user.toml`（新建） | 文件存在；gitignore 已排除 |
| 0.1.3 | 实现 `load_config()` 三层覆盖合并 | `scripts/config_loader.py`（新建） | 三层覆盖逻辑正确；缺失文件时降级不 crash |
| 0.1.4 | 新增 `/animus-config` 命令 | `commands/animus-config.md`（新建） | 命令可列出/修改配置项 |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G0.1.1 | ◎ | `python -c "import tomllib; tomllib.load(open('.claude/animus/config.toml','rb'))"` | JSON/TOML 解析成功，所有字段存在 |
| G0.1.2 | ◎ | 修改 `config.toml[review].strictness = "low"` | `load_config()` 返回 `low` |
| G0.1.3 | ◎ | 删除 `config.toml` | `load_config()` 返回 DEFAULT_CONFIG |
| G0.1.4 | ◎ | 同时存在 config.toml 和 config.user.toml，用户层覆盖 team 层 | user 层值生效 |
| G0.1.5 | ○ | `config.user.toml` 在 `.gitignore` 中 | `git status` 不显示该文件 |

---

### Sprint 0.2：引擎脚本化（⑥）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 0.2.1 | 创建 `scripts/animus-engine.py` 入口 | `animus-engine.py`（新建） | argparse 解析正确，7 个子命令存在 |
| 0.2.2 | 实现 `cmd_status.py` | `engine/cmd_status.py`（新建） | 输出与 `/animus-status` 一致 |
| 0.2.3 | 实现 `cmd_transition.py` | `engine/cmd_transition.py`（新建） | PS 版状态机逻辑完整翻译，包含所有分支 |
| 0.2.4 | 实现 `cmd_validate.py` | `engine/cmd_validate.py`（新建） | features.json 校验通过/失败输出正确 |
| 0.2.5 | 实现 `cmd_archive.py` | `engine/cmd_archive.py`（新建） | 归档 + 清空 + 迭代编号正确 |
| 0.2.6 | 实现 `cmd_rebuild.py` | `engine/cmd_rebuild.py`（新建） | 从 memlog 重建成 features.json（见 Phase 1 memlog） |
| 0.2.7 | 现有 `.md` 命令和 hooks 改为调 engine CLI | 所有 command/hook 文件 | 输出格式不变 |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G0.2.1 | ◎ | `python animus-engine.py status` | 输出 JSON，包含 task_count |
| G0.2.2 | ◎ | `python animus-engine.py transition T001 in_progress` | features.json 中 T001.status = "in_progress" |
| G0.2.3 | ◎ | `python animus-engine.py transition T001 passed`（无 verify_command） | 拒绝流转，exit 1 |
| G0.2.4 | ◎ | `python animus-engine.py transition T001 failed`（非法流转：in_progress→failed） | 拒绝流转，exit 1 |
| G0.2.5 | ◎ | `python animus-engine.py validate` | 检查 features.json 结构 + 循环依赖 |
| G0.2.6 | ◎ | `python animus-engine.py archive --name "测试迭代"` | 归档目录创建，features.json 已清空 |
| G0.2.7 | ○ | 对所有合法和非法流转组合执行 | 合法通过、非法拒绝 |
| G0.2.8 | ○ | PS 版 `animus-engine.py transition` 与 Python 版输出对比 | 100% 一致 |

### Phase 0 通过门控（整体）

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G0.FINAL | ◎ | 全子命令遍历：status/transition/validate/archive | 全部无错误返回 |
| G0.FINAL | ◎ | 配置 + engine 联动：改 config 后 engine 行为变化 | 配置生效 |
| G0.FINAL | △ | 所有新增 Python 文件 `python -m py_compile` | 语法通过 |

---

## Phase 1：核心体验（Sprint 1.1 – 1.4）

**工期：** 第 3-4 周
**前置依赖：** Phase 0 通过 G0.FINAL
**产出：** 命名 Agent + memlog + 命令别名 + Quick Dev 五路路由

---

### Sprint 1.1：命名 Agent 角色系统（①）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 1.1.1 | 22 个 agent frontmatter 加 name/title/team | 所有 agent 文件 | 每个文件有 3 字段 |
| 1.1.2 | 5 个核心 agent 加 persona 描述 | 5 个核心 agent | persona 字段存在，50-100 字 |
| 1.1.3 | 更新 agent-index.md | `docs/agent-index.md` | 表格含 name/team 列 |
| 1.1.4 | 更新 plugin.json description | `.claude-plugin/plugin.json` | description 提及命名 agent |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G1.1.1 | ◎ | 脚本遍历所有 agent 文件，检查 frontmatter | 22 个文件全部通过 |
| G1.1.2 | ◎ | 手动读 5 个核心 agent 文件 | persona 内容正确，无空值 |
| G1.1.3 | ○ | `grep "team:" agents/*/*.md` 无空值 | 所有 team 字段有值 |

---

### Sprint 1.2：Memlog 持久化（②）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 1.2.1 | 定义 memlog 目录格式 + 事件文件模板 | 新建 `.claude/animus/memlog/` | 目录存在，模板文件正确 |
| 1.2.2 | 实现 `cmd_rebuild.py`（从 memlog 重建） | `engine/cmd_rebuild.py` | 可以重建 features.json |
| 1.2.3 | 新建 `migrate-to-memlog.py` | `scripts/migrate-to-memlog.py`（新建） | 一次性转换现有 features.json |
| 1.2.4 | 修改 `update-progress.py` 写入改为 memlog | `scripts/update-progress.py` | 状态变更 → memlog 事件 |
| 1.2.5 | 修改 hooks/pre-compact | `pre-compact.ps1/.sh` | 只追加 memlog，删除多文件同步 |
| 1.2.6 | 删除 handoff/continue 命令 | 删除 2 个 md + 修改 plugin.json | 命令不可用 |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G1.2.1 | ◎ | 执行迁移脚本 → 删除 features.json → `python animus-engine.py rebuild` | features.json 内容与原一致 |
| G1.2.2 | ◎ | 执行 10 次任务状态变更 → rebuild | features.json 反映最新状态 |
| G1.2.3 | ◎ | `/animus-dev` 在 memlog 存在且 features.json 为空时 | 输出「检测到上次进度，已恢复」 |
| G1.2.4 | ◎ | `/animus-handoff` 访问 | 返回"命令未找到" |
| G1.2.5 | ◎ | rebuild 性能：200 个事件 | < 50ms |
| G1.2.6 | ○ | memlog 文件用 UTF-8 编码；中文文件名和内容正确 | 无乱码 |

---

### Sprint 1.3：命令别名（③）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 1.3.1 | plugin.json 加 aliases | `plugin.json` | aliases 注册正确 |
| 1.3.2 | 新建 `/animus-help` | `commands/animus-help.md`（新建） | 根据状态推荐下一步 |
| 1.3.3 | readme 加速查指南 | `docs/README.md` | 场景→命令映射表存在 |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G1.3.1 | ◎ | `/dev` `/status` `/review` | 3 个别名可用 |
| G1.3.2 | ◎ | `/animus-help` 在无 features.json 时 | 推荐 `/animus-init` |

---

### Sprint 1.4：Quick Dev 五路路由（⑤）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 1.4.1 | 新建 `commands/animus-dev.md`（四路路由） | `animus-dev.md`（新建） | 4 条路由（debug/fast/light/full） |
| 1.4.2 | 实现路径确认提示 | 同上 | AI 选路后问用户确认 |
| 1.4.3 | 删除 `animus-plan.md` 和 `animus-debug.md` | 删除 2 个文件 | 命令不可用 |
| 1.4.4 | 实现 write-gate hook | `write-gate.sh/.ps1`（新建） | 无任务时拦截 Write/Edit |
| 1.4.5 | 更新 plugin.json | `plugin.json` | 注册 animus-dev |
| 1.4.6 | 实现 autonomous 模式 | 引用 config.toml | autonomous=true 时跳过确认 |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G1.4.1 | ◎ | 场景矩阵测试（每路由至少 2 个场景） | 五路路由全部走通 |
| **场景矩阵：** |
| | debug | "PDF 导出崩溃" + "按钮点不动" | 走 debug-path，3 问调试专用 Grilling | 2/2 |
| | fast | "改按钮间距" + "加个 tooltip" | 1 问确认 | 2/2 |
| | light | "加导出功能" + "重构 sidebar" | 3 问 | 2/2 |
| | full | "重构数据层" + "加 User 系统" | 7 问 | 2/2 |
| G1.4.2 | ◎ | debug-path：features.json 有 type/severity/repro_steps/root_cause | 5 个字段全存在 |
| G1.4.3 | ◎ | write-gate：无 in_progress 时 Write 一个 .cpp | 被拦截 |
| G1.4.4 | ◎ | write-gate：有 in_progress 时 Write 同一个文件 | 放行 |
| G1.4.5 | ◎ | write-gate：Write `.claude/animus/features.json` | 放行（白名单） |
| G1.4.6 | ◎ | `config.toml[gates].require_task_before_write = false` | 门控关闭，放行 |
| G1.4.7 | ◎ | `/animus-plan` `/animus-debug` 访问 | 返回"命令未找到" |
| G1.4.8 | ○ | `config.toml[dev].autonomous = true` + `/animus-dev 修 bug` | 跳过确认，AI 自主选路 |

### Phase 1 通过门控（整体）

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G1.FINAL | ◎ | 全链路端到端：`/animus-dev --full 加 PDF 导出` → Grilling → features.json → implement → review → passed | 完整走通 |
| G1.FINAL | ◎ | 全链路端到端：`/animus-dev PDF 导出崩溃` → debug 3 问 → features.json → implement → review → passed | 完整走通 |
| G1.FINAL | ◎ | memlog 结束状态正确（创建任务 + 状态变更 + 审查通过事件） | 所有事件可追溯 |
| G1.FINAL | ◎ | 删除 features.json → `/animus-dev` → 自动恢复进度 | 恢复成功 |
| G1.FINAL | △ | 场景覆盖：10 个不同意图 → 路由正确 | 10/10 |

---

## Phase 2：能力增强（Sprint 2.1 – 2.4）

**工期：** 第 5-8 周
**前置依赖：** Phase 1 通过 G1.FINAL
**产出：** 工作流地图 + 对抗审查 + Party Mode + 头脑风暴

---

### Sprint 2.1：工作流地图（④）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 2.1.1 | `cmd_status.py` 加 WORKFLOW_GRAPH dict | `engine/cmd_status.py` | 7 个命令的 pre/post/next 正确定义 |
| 2.1.2 | 实现推荐逻辑（按优先级匹配） | 同上 | 推荐第一条匹配的建议 |
| 2.1.3 | `/animus-status` 输出追加推荐块 | `commands/animus-status.md` | 输出含"推荐下一步"区块 |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G2.1.1 | ◎ | 状态机遍历测试（4 种状态 × 对应推荐） | 4/4 推荐正确 |
| G2.1.2 | ◎ | DAG 缺失任一命令时 | 不 crash，跳过该命令推荐 |

---

### Sprint 2.2：对抗性审查（⑦）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 2.2.1 | 新建 3 个审查 agent | `edge-case-hunter.md` `acceptance-auditor.md` `ponytail-reviewer.md`（新建） | 每个 agent 有 frontmatter 和审查逻辑 |
| 2.2.2 | 改 `/animus-review` 为 4 agent 并行 | `commands/animus-review.md` | 并行调用 + 结果聚合 |
| 2.2.3 | 实现 3 轮循环回退 | 同上 | 见门控 |
| 2.2.4 | 实现严格模式超时降级 | 同上 | 见门控 |
| 2.2.5 | 更新 `cmd_validate.py` 门控逻辑 | `engine/cmd_validate.py` | 四审无 high → passed |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G2.2.1 | ◎ | 提交含 high 级 bug 的代码 → 审查 | code-reviewer 报 high |
| G2.2.2 | ◎ | high 阻塞 → implementer 修复 → 重新审查 | 第 2 轮审查无 high |
| G2.2.3 | ◎ | 连续 3 轮仍有 high | 审查终止，报错 |
| G2.2.4 | ◎ | 某个 agent 超时 | 自动重试，3 次后降级终止 |
| G2.2.5 | ◎ | 提交含 medium 级问题的代码 | 不阻塞，标记待确认 |
| G2.2.6 | ◎ | 提交含过度工程的代码 | ponytail-reviewer 报 low/medium |
| G2.2.7 | ○ | 4 agent 并行耗时 | < 最慢 agent 耗时 × 1.2 |

---

### Sprint 2.3：Party Mode（独立 Skill）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 2.3.1 | 新建 `skills/party-mode/SKILL.md` | `SKILL.md`（新建） | 辩论流程编排入口 |
| 2.3.2 | 定义 2 个模板（架构评审团 + 代码审查团） | `templates/arch-review.json` `code-review.json` | 角色/persona 完整 |
| 2.3.3 | 实现 4 种运行模式 | `SKILL.md` + `customize.toml` | session/subagent/auto/agent-team |
| 2.3.4 | 手动入口 `/animus-party` | `commands/animus-party.md`（新建） | 可选模板和模式 |
| 2.3.5 | dev-full 自动触发 | `commands/animus-dev.md` | 7 问后触发，ask_before_start 询问 |
| 2.3.6 | 辩论结果写入 spec + memlog | — | 共识写入 spec.constraints/risks |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G2.3.1 | ◎ | `/animus-party --template arch-review --mode session` | 5 角色依次发言 |
| G2.3.2 | ◎ | `/animus-party --template code-review --mode subagent` | 4 角色独立输出审查意见 |
| G2.3.3 | ◎ | `/animus-dev --full 加架构改动` → 辩论自动触发 | 辩论启动前询问用户 |
| G2.3.4 | ◎ | 辩论结束后 | memlog 有辩论事件；spec.constraints/risks 已更新 |
| G2.3.5 | ◎ | `config.toml` 改 `ask_before_start = false` | 辩论不打问直接启动 |
| G2.3.6 | ○ | `--mode agent-team` 在 Claude Code 中 | 角色跨会话持久 |

---

### Sprint 2.4：头脑风暴（⑧）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 2.4.1 | 新建 6 个技法实现 | `skills/brainstorming/`（新建） | 每个技法独立文件 |
| 2.4.2 | 集成到 dev-full 7 问之前 | `commands/animus-dev.md` | 自动检测需要脑暴 |
| 2.4.3 | 脑暴结果写入 spec | 同上 | spec 5 字段自动填充 |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G2.4.1 | ◎ | 技法 × 场景矩阵（6 技法 × 2 场景 = 12 个测试） | 12/12 正确激活 |
| G2.4.2 | ◎ | 脑暴完成后 | features.json spec 已填充 |
| G2.4.3 | ◎ | 拒绝脑暴 | 回退到标准 7 问 Grilling |

### Phase 2 通过门控（整体）

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G2.FINAL | ◎ | `/animus-dev --full 加功能` → 脑暴（可选）→ 7 问 → Party Mode 辩论 → implement → 4 agent 审查 → 3 轮回退 | 全链路走通 |
| G2.FINAL | ◎ | `/animus-status` 底部推荐正确 | 每种状态推荐准确 |
| G2.FINAL | ◎ | memlog 全事件类型覆盖：创建/状态变更/决策/归档/辩论 | 6 种事件全部存在 |

---

## Phase 3：深度建设（Sprint 3.1）

**工期：** 第 9-10 周
**前置依赖：** Phase 2 通过 G2.FINAL
**产出：** SPEC 内核 + 4 条法则校验

---

### Sprint 3.1：SPEC 内核（⑩）

**任务清单：**

| # | 任务 | 涉及文件 | 验收条件 |
|---|------|---------|---------|
| 3.1.1 | `cmd_validate.py` 加 4 条法则校验 | `engine/cmd_validate.py` | why/success/constraints/non_goals 校验 |
| 3.1.2 | dev-full Grilling 输出包含完整 SPEC | `commands/animus-dev.md` | 5 字段自动填充 |
| 3.1.3 | acceptance-auditor 按 spec.success 逐条验证 | `acceptance-auditor.md` | PASS/FAIL 逐条判定 |

**验证门控：**

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G3.1.1 | ◎ | 4 条法则各 2 个用例（合法 + 非法） | 8/8 判断正确 |
| G3.1.2 | ◎ | why 为空 → validate 报 WARNING | WARNING 输出正确 |
| G3.1.3 | ◎ | success 为空 → validate 报 WARNING | WARNING 输出正确 |
| G3.1.4 | ◎ | full-path 的 spec 不满足 4 条法则 → 拒绝进入 implement | 阻塞通过 |
| G3.1.5 | ○ | non_goals 为空数组 → validate 报 WARNING | WARNING 输出正确 |

### Phase 3 通过门控（整体）

| 门控 | 级别 | 验证方法 | 通过标准 |
|------|------|---------|---------|
| G3.FINAL | ◎ | `/animus-dev --full` 全部 spec 5 字段满足 4 法则 | 通过 validate |
| G3.FINAL | ◎ | acceptance-auditor 验证 spec.success 准确 | PASS 与人工验证一致 |

---

## 回归测试矩阵

每次 Phase 通过后，在 C++/Qt、Rust、Python 三个目标工程上执行：

```
2. /animus-dev 修个 bug（debug-path）
3. /animus-dev --full 加个小功能（含脑暴 + Party Mode）
4. /animus-review 审查
5. python animus-engine.py archive --name "回归测试迭代"
6. 删除 features.json → /animus-dev → 自动恢复
7. python animus-engine.py rebuild
8. python animus-engine.py validate
```

**通过标准：**
- 步骤 1-8 全部无报错完成
- memlog 含 创建任务 + 状态变更 + 决策 + 辩论 + 归档 全部事件
- config.toml 配置在所有环境中生效

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| PowerShell 状态机翻译遗漏分支 | Phase 0 延迟 | G0.2.8：PS/Python 输出对比，逐条覆盖 |
| memlog 文件数膨胀（1000+ 事件） | 性能下降 | G1.2.5：性能测试门控；后续考虑按季度归档 |
| 4 agent 审查 token 消耗过大 | Phase 2 成本超预期 | Party Mode 默认 session 模式降级；`config.toml` 可选 subagent |
| Party Mode 子 agent 互相冲突 | 输出不可用 | debate 最大轮数限制 3 轮 |
| Bug 误判为 Feature 走错路由 | 用户体验差 | 路径确认机制 + `--debug`/`--full` 手动覆盖 |
