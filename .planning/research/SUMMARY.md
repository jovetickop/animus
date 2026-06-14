# Project Research Summary

**Project:** ty-qt-ai-plugin (harness-cc)
**Domain:** Claude Code 技能插件 / 多语言代码审查编排框架
**Researched:** 2026-06-14
**Confidence:** HIGH

## Executive Summary

harness-cc 是一个 Claude Code 技能插件式的多语言编码工作流引擎，采用三层微内核架构（技能入口 -> 编排命令 -> 执行 Agent），覆盖 6 种语言（C++/Qt, C++/CMake, Python, Node.js, Rust, Go）的代码格式化、代码审查、状态机进度跟踪和跨平台 hooks 系统。经过 4 个并行研究方向的深入调研，核心结论是：**该项目是一个成熟度较高的 brownfield 项目——MVP 已经构建并验证通过，当前里程碑是对 11 项技术债务的系统化修复，而非从零开发新功能。**

四个研究方向（技术栈、功能全景、架构评估、陷阱分析）的发现高度收敛，确认了以下共识：(1) 当前 UTF-16LE 编码混乱必须优先统一为 UTF-8 with BOM，这是其他所有修复的前提；(2) 状态机引擎（pending -> in_progress -> passed/failed + Oracle 验证）是该插件在整个 Claude Code 技能生态中的核心差异化优势，行业内无直接竞品；(3) GBK/UTF-8 编码桥接是另一个独有壁垒，在 English-language 生态中未发现其他技能提供此能力；(4) 所有修复应分 3 个阶段顺序推进，**编码统一必须先于安全和模块化修复**，否则 Git diff 无法正确阅读变更。

主要风险来自陷阱叠加效应——多个技术债务问题集中在同一文件（如 `update-progress.ps1` 同时存在 UTF-16LE 编码、CRLF/LF 混用、单脚本多职责、中文注释损坏），修复顺序错误会导致重复工作。措施是严格遵守编码先行的依赖顺序，每个阶段完成后进行全语言回归验证。整体置信度高，四个研究方向的官方文档和 community 实践高度一致。

## Key Findings

### Recommended Stack

技术栈研究（STACK.md）确认了四个关键技术维度的最佳实践选择：

**核心技术决策：**

- **PowerShell 源文件编码: UTF-8 with BOM** — 这是 PowerShell 5.1 和 7.x 均能正确识别的唯一编码，解决了 UTF-16LE 导致 Git diff 不可读和中文乱码的问题
- **文件输出操作: 始终显式指定 `-Encoding utf8`** — 避免 `Out-File`（默认 UTF-16LE）和 `Set-Content`（默认 ANSI）在两个 PowerShell 版本间的行为差异
- **Python 2/3 双兼容: `from __future__` + `sys.version_info` 标准模式** — 维持零第三方 Python 依赖策略，不引入 `six` 或 `python-future`
- **多语言格式化编排: 继续使用 `format-all.py`（零依赖，~200 行）** — reviewdog 的 rdjson 格式值得参考，但当前方案对于 PostToolUse hook 场景是更轻量的选择
- **Claude Code 插件架构: 维持当前三层架构，新增 `.claude-plugin/plugin.json`** — 当前 `SKILL.md -> commands/ -> agents/ + rules/` 分层完全符合官方推荐模式，plugin manifest 可兼容添加

**关键不推荐项：**
- 避免 UTF-16LE（Git 不可读、中文乱码，已有历史证明）
- 避免 UTF-8 without BOM（PS 5.1 环境下会误判为 ANSI）
- 避免 `Invoke-Expression`（安全风险，已被 PSScriptAnalyzer 标记）
- 避免将 MegaLinter/SonarQube 嵌入 PostToolUse hook（启动延迟过长）

### Expected Features

功能研究（FEATURES.md）覆盖 4 个领域（多语言格式化管线、状态机进度跟踪、AI Agent 技能插件生态、跨平台 hooks 集成），对比了 12 个行业竞品和社区项目。

**Must have（已全部实现）：**
- 文件写入自动格式化（PostToolUse hook） — 已通过 `clang-format` + `format-all.py` 实现
- 状态转换验证 + 依赖跟踪 — 已通过 `update-progress.ps1` 实现 5 状态矩阵 + `depends_on` DAG 检查
- 同一时间仅单个活跃任务 — 已强制实现，防止并行混乱
- 进度日志/审计追踪 — 已通过 `claude-progress.txt` + 报告生成实现
- 跨平台 hooks（PreToolUse/PostToolUse/PreCompact/Stop） — 全部实现，bash+PowerShell 双降级
- 项目类型自动检测 — 支持 6 种项目类型自动识别
- Agent 定义按领域组织 — 23 个 Agent + 12 个规则文件

**Should have（差异化优势）：**
- **GBK/UTF-8 编码桥接** — 中国 Windows C++ 项目中独有的透明编码转换，竞品均不具备
- **Oracle 验证（构建+测试证据需求）** — 从 `in_progress` 到 `passed` 必经构建+测试验证，防止"以后补测试"
- **状态机作为技能编排核心** — 与 Claude Code 会话生命周期（PreCompact/Stop hooks）集成
- **多语言 Agent 专门化** — 6 种语言各自独立的 architect/implementer/tester/reviewer 角色
- **会话韧性** — PreCompact hook 在上下文压缩前持久化状态，Stop hook 生成恢复指引

**Defer（v1.x 或 v2+）：**
- 异步 PostToolUse 日志（`"async": true`）— 零延迟增加审计能力
- `/resume` 显式命令 — 包装 Stop hook 输出为结构化恢复流程
- Hook `--verbose` 调试模式 — 从 `/dev/null` 重定向中暴露错误
- Marketplace 插件打包 — 通过 Claude Code 插件市场分发
- 格式化预设按项目类型调整 — 将 `project-config.json` 的 `type` 字段关联到格式化配置

### Architecture Approach

架构研究（ARCHITECTURE.md）系统评估了当前架构状态，确认了三层微内核架构的有效性，同时识别了从有机增长产生的结构性债务。

**当前架构评估：**

| 子系统 | 当前状态 | 问题 |
|--------|----------|------|
| 状态机引擎 | `update-progress.ps1` 单文件 424 行 | 违反单一职责；验证、Oracle、报告、Git 提交混在一起 |
| Hook 脚本 | 12 个文件在 `hooks/scripts/` | 路径查找逻辑重复 6+ 次；编码转换职责边界不清 |
| 路径解析 | 每个脚本独立实现 | 5+ 种不同方法：`$PSScriptRoot/../../..`、`cd` 遍历、CWD 相对路径 |
| 编码桥接 | `encoding-bridge.py` + inline 在 hooks 中 | 调用者不一致；哪些脚本该调用哪些不该调用无文档 |
| 插件清单 | 无 `plugin.json` | 先于官方插件规范，缺少标准发现机制 |
| 脚本目录 | 分散在 `scripts/` 和 `.claude/scripts/` | 双目录所有权不清 |

**建议的架构改进（按优先级排序）：**

1. **路径解析集中化** — 创建 `scripts/shared/resolver.py` + `path-resolver.ps1`，所有脚本调用统一模块
2. **`update-progress.ps1` 分解为领域模块** — 拆分为 `validate-transition.ps1`、`oracle-runner.ps1`、`report-generator.ps1`、`progress-logger.ps1`、`git-helper.ps1`，原脚本变为 ~30 行编排器
3. **脚本目录标准化** — `scripts/shared/` 放跨域工具，`scripts/formatters/` 放格式化器，`hooks/scripts/` 仅保留薄胶合脚本
4. **编码桥接边界制度化** — 仅 PreToolUse/PostToolUse 两个 hooks 接触编码转换，其他脚本只读写 UTF-8
5. **添加 `plugin.json`** — 通过自定义路径指回现有 `.claude/` 结构，保持向后兼容

### Critical Pitfalls

陷阱研究（PITFALLS.md）识别了 15 个陷阱（5 个关键、7 个中等、3 个轻微），全部在当前代码库中得到验证。

**5 个关键陷阱：**

1. **PowerShell 默认编码契约（Pitfall 1）** — 当前 7 个 UTF-16LE .ps1 文件导致 Git 视作二进制、diff 不可读、中文注释损坏。修复：UTF-8 with BOM，禁止裸 `>` 重定向。**Phase 1 解决。**

2. **Invoke-Expression 命令执行（Pitfall 2）** — `run-regression.ps1` 中 3 处使用 `Invoke-Expression` 执行配置命令，PSScriptAnalyzer 标记为高危。修复：替换为 `&` 调用运算符 + `Start-Process`。**Phase 2 解决。**

3. **Shell 脚本换行符污染（Pitfall 3）** — `.claude/hooks/scripts/` 下所有 `.sh` 文件使用 CRLF，在 WSL/macOS/Linux 上 `#!/bin/bash\r` 直接报错。修复：`.gitattributes` 强制 `.sh text eol=lf` + `dos2unix` 转换。**Phase 1 配合解决。**

4. **正则解析 JSON 脆弱性（Pitfall 4）** — `clang-format.ps1` 和 `pre-tool-use.ps1` 用 `-notmatch` 正则提取 JSON 字段，转义引号和格式化变化时静默失败。修复：替换为 `ConvertFrom-Json`。**Phase 2 解决。**

5. **Hooks 双平台降级调试真空（Pitfall 5）** — `2>/dev/null` 吞噬所有错误，bash 因 CRLF 失败后降级到 PowerShell 也失败，`|| exit 0` 让一切看起来正常。修复：日志文件 + 条件 DEBUG 模式 + 文档说明。**Phase 2-3 解决。**

**陷阱叠加效应：** `update-progress.ps1` 同时具有 Pitfall 1（UTF-16LE）、Pitfall 3（CRLF/LF 混用）、Pitfall 7（400+ 行单脚本多职责），编码统一必须先于模块化拆分。

## Implications for Roadmap

基于四个研究文件的高度收敛结论，建议按 **3 个阶段** 顺序推进技术债务修复，每阶段有严格的前置依赖。

### Phase 1: 编码统一与基础设施标准化 (Foundation)

**Rationale:** 此阶段是所有后续修复的前提——如果文件不是 UTF-8 with BOM 且换行符不统一，Git diff 无法正确显示后续任何变更，安全性修复和模块化拆分都将无法审查。ARCHITECTURE 和 PITFALLS 一致要求此阶段最先执行。

**Addresses (TECHD card):** TECHD-01（编码统一）、TECHD-02（换行符修复）、TECHD-03（中文注释修复）、TECHD-04（状态路径统一）、TECHD-05（模板角色澄清）

**Delivers:**
- 所有 `.ps1` 文件转为 UTF-8 with BOM，Git diff 可读
- 所有 `.sh` 文件转为 LF 换行符，跨平台正常工作
- 已损坏的中文注释恢复
- `.claude/state/` 作为唯一的 `features.json` 标准路径
- `templates/state/` 目录清理，角色文档化
- 新增 `.gitattributes` 和 `.editorconfig`

**Avoids:** Pitfall 1（UTF-16LE 编码混乱）、Pitfall 3（Shell 换行符 CRLF）、Pitfall 11（状态文件路径分裂）、Pitfall 13（Git 属性缺失）、Pitfall 14（EditorConfig 缺失）

**Research flag:** 此阶段有标准模式。编码转换的 PowerShell 命令已有已验证的脚本，无需额外研究。需要关注的是 `.git-blame-ignore-revs` 配置，避免编码转换污染 Git blame。

---

### Phase 2: 安全加固与鲁棒性提升 (Security & Robustness)

**Rationale:** 依赖 Phase 1 完成（文件编码正确后才可以安全地修改内容）。此阶段解决两个已由 PSScriptAnalyzer 和社区共识明确标记的安全风险（`Invoke-Expression`、JSON 正则解析），以及一个性能问题（`cargo fmt` 双重执行）。

**Addresses (TECHD card):** TECHD-07（Invoke-Expression 替换）、TECHD-08（JSON 正则解析修复）、TECHD-09（Rust 格式化缓存）

**Delivers:**
- `run-regression.ps1` 和所有脚本中 `Invoke-Expression` 被 `&` + `Start-Process` 替换
- Hook 脚本全部使用 `ConvertFrom-Json` 替代正则解析 JSON
- `format-all.py` 中 `cargo fmt --check` 去除，`Cargo.toml` 目录查找加入 LRU 缓存

**Uses from STACK:** `& $cmd 2>&1` 调用运算符模式（替代 `Invoke-Expression`）、`ConvertFrom-Json`（替代正则解析）

**Avoids:** Pitfall 2（Invoke-Expression 注入）、Pitfall 4（JSON 正则脆弱性）、Pitfall 10（格式化空转/缓存缺失）

**Research flag:** 此阶段有高度标准化的模式。`Invoke-Expression` 替代方案有 Microsoft 官方文档提供 5 种分级方案。JSON 解析在 PS 5.1 和 7+ 都原生支持。**无需额外研究。**

---

### Phase 3: 模块化拆分与文档补充 (Modularization & Documentation)

**Rationale:** 依赖 Phase 2 完成（在代码安全性已验证的基础上拆分职责）。此阶段解决最大单文件（424 行 `update-progress.ps1`）的模块化问题，以及两个配置/文档缺陷。

**Addresses (TECHD card):** TECHD-06（脚本拆分）、TECHD-10（硬编码路径修复）、TECHD-11（文档补充）

**Delivers:**
- `update-progress.ps1` 拆分为 5 个领域模块 + 1 个薄编排器（~30 行）
- `init-project.ps1` 中 `$env:USERPROFILE` 硬编码替换为 `$PSScriptRoot` 或 `$env:CLAUDE_PLUGIN_ROOT`
- 补充 3 个文档章节：编码策略详解、JSON 模板角色说明、Hook 调试方法

**Implements (architecture):** 路径解析集中化（`scripts/shared/resolver.py`）、编码桥接边界制度化、双平台降级脚本转换为薄 Python 调用器模式

**Avoids:** Pitfall 5（Hooks 调试真空）、Pitfall 7（单脚本多职责膨胀）、Pitfall 8（Dot-Sourcing 副作用泄漏）、Pitfall 12（硬编码用户路径）

**Research flag:** 此阶段需要适度研究。模块化拆分的模式有 PowerShell 社区最佳实践（Mike F. Robbins 设计哲学），但需要确认 `.psm1` 模块在 PS 5.1 和跨平台环境下的兼容性。建议在 Phase 3 开始前做一次 `plan-phase` 研究，重点测试 PS 5.1 的模块加载行为。

---

### Phase Ordering Rationale

```
Foundation (Phase 1) --必须先于--> Security (Phase 2) --必须先于--> Modularization (Phase 3)
    编码统一                   安全修复                   模块拆分
    换行符修复                 性能修复                   文档补充
    路径标准化                （依赖可读文件）            （依赖已安全代码）
```

架构研究明确警告："Phase 3 绝不能先于 Phase 2——在路径逻辑分散时拆分脚本，会产生 7 个需要更新的位置而非 1 个。" 陷阱研究进一步指出："不能在编码修复和代码修复之间反复切换——每次编码转换都会使之前的 diff 变得不可阅读。" 两个研究的独立结论完全一致。

**分组逻辑：**
- **Phase 1 分组依据：** 所有文件层面的基础设施修改（编码、换行符、路径）对彼此有影响，必须一次性完成。如果不先确定标准路径（TECHD-04），模板角色清理（TECHD-05）无法进行。
- **Phase 2 分组依据：** 安全性修复和性能修复都涉及代码逻辑修改，在编码统一的基础上进行可以确保 Git diff 正确反映意图。
- **Phase 3 分组依据：** 模块拆分和文档补充是"收尾型"工作，在代码已有正确行为的基础上优化可维护性。

### Research Flags

需要额外研究的阶段：
- **Phase 3：** 需要研究 PowerShell 5.1 下的 `.psm1` 模块加载行为、`CLAUDE_PLUGIN_ROOT` 和 `CLAUDE_PLUGIN_DATA` 在目标项目中的可用性。Reason: niche 平台细节，非标准模式。

可跳过额外研究的阶段：
- **Phase 1：** 编码转换模式高度标准化，有已验证的 PowerShell 转换脚本
- **Phase 2：** `Invoke-Expression` 替换有 Microsoft 官方 5 级指引；`ConvertFrom-Json` 是原生 API；`cargo fmt` 缓存模式在社区广泛使用

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Microsoft 官方文档 + PSScriptAnalyzer 规则 + 已验证的正确性证据（TECHD-01 编码问题已确认）。Python 2/3 兼容策略有 Python 官方移植指南支撑。Claude Code 插件架构有 Anthropic 官方参考实现 |
| Features | HIGH | 4 个领域的调研覆盖 12 个竞品/社区项目，发现高度收敛。编码桥接和多语言 Agent 专门化的"唯一性"声明在 English-language 生态中已确认 |
| Architecture | HIGH | 模式来源自 PowerShell 社区标准（mikefrobbins.com）、Claude Code 官方 plugin spec、TAKT 工作流模式。当前架构评估完全基于代码库实际的 CONCERNS.md 分析 |
| Pitfalls | HIGH | 所有 15 个陷阱在当前代码库中均有对应的具体文件和行号验证。恢复策略已在实际项目中测试过（commit 628f02c 确认中文注释损坏） |

**Overall confidence:** HIGH

**置信度说明：** 四个研究方向来自不同来源（官方文档、社区实践、代码库分析、竞品对比），但结论高度收敛。唯一的不确定性在于："GBK/UTF-8 编码桥接是否真的独一无二"——在 English-language 搜索结果中未发现竞品，但不排除中文生态中有类似解决方案。

### Gaps to Address

1. **PowerShell 5.1 模块加载兼容性** — Phase 3 的 `.psm1` 模块拆分需要验证在 PS 5.1 下的实际加载行为。建议在 Phase 3 开始前用一个原型验证。如果 PS 5.1 不支持某些模块特性，则需要回退到 dot-sourcing 方案（附带作用域隔离措施）。

2. **SonarQube vs reviewdog 的 diff-aware 深度对比** — 当前信息不足以决定是否在 CI 场景中推荐 reviewdog 替代 SonarQube。但此决策不属于当前技术债务修复范围，可延迟到未来 CI 集成需求出现时。

3. **`CLAUDE_PLUGIN_ROOT` 在目标项目中的可用性** — 如果在目标项目环境中该变量未设置，当前 `init-project.ps1` 的路径探测逻辑可能需要 fallback。Phase 3 修复 TECHD-10 时需要额外留意。

4. **Claude Code Plugin Manifest schema 完整度** — 当前官方文档对 `plugin.json` 的 schema 描述不够完整。如果需要 marketplace 发布，需要进一步研究。Phase 3 建议仅创建最小可用版本，不做完整发布。

5. **全语言回归测试的自动化** — 当前回归测试需手动在 3 种语言的目标工程中跑完整链路。如果 Phase 1 的编码转换导致预期之外的问题，回归测试的工作量会很大。建议 Phase 1 完成后为每个语言创建标准化的回归测试脚本。

## Sources

### Primary (HIGH confidence)
- Microsoft Learn: "PowerShell Default Output Encoding" — 编码策略官方文档
- Microsoft: "Avoid using Invoke-Expression" — 安全指南
- Microsoft: "Preventing script injection attacks" — 脚本注入防御指南
- Microsoft Docs: "ConvertFrom-Json (PowerShell 5.1)" — JSON 解析 API
- GitHub Docs: "Configuring Git to handle line endings" — 换行符配置
- Claude Code Hooks Reference (code.claude.com) — 4 个钩子点的官方配置模式
- Claude Code Plugins Reference (code.claude.com) — Plugin manifest schema
- Claude Code Official Plugin Structure (github.com/anthropics) — 目录布局规范
- Python Official Porting Guide — Python 2 -> 3 双兼容模式
- PSScriptAnalyzer: "AvoidUsingInvokeExpression" — 官方规则文档
- GitHub: "git-for-windows working-tree-encoding bug #5078" — UTF-16 编码问题

### Secondary (MEDIUM-HIGH confidence)
- Mike F. Robbins: "PowerShell Script Module Design Philosophy" — 模块化最佳实践
- SFEIR Institute: "Custom commands and skills - Common mistakes" — Claude Code 技能开发错误排名
- GitHub: claude-code-extensions (nodnarbnitram) — 18 技能/21 插件/60+ Agent 参考实现
- GitHub: claude-skills (alirezarezvani) — 338 技能最大集合参考
- Lefthook (evilmartians) — 并行跨平台 git hooks 参考
- pre-commit 文档 — 多语言 git hooks 框架模式对比
- MegaLinter 文档 — 多语言格式化管线架构参考
- TAKT Agent Koordination Topology (nrslib) — 声明式 YAML 工作流
- PowerShellPracticeAndStyle: "Building Reusable Tools" — 工具 vs. 控制器区分
- GitHub: "PreToolUse updatedInput bug #39814" — 已知 hooks 问题跟踪

### Tertiary (MEDIUM confidence)
- CSDN: "Windows 11 23H2 BOM 处理逻辑改写" — 编码契约变更（需交叉验证）
- GitHub: "orchestrator bypasses start-task hooks #315" — inline 执行绕过 hooks 问题
- morphllm.com: "Skills vs MCP vs Plugins" 决策框架对比

---
*Research completed: 2026-06-14*
*Ready for roadmap: yes*