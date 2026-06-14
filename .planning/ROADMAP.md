# Roadmap: ty-qt-ai-plugin (harness-cc)

**Core Value:** 让 AI 辅助的编码工作可跟踪、可验证、可重复
**Milestone:** v3 技术债务修复 — 11 项 TECHD 项
**Granularity:** Coarse (3 phases)
**Created:** 2026-06-14

---

## Phases

- [ ] **Phase 1: Foundation** — 编码统一与基础设施标准化（5 项 TECHD）
- [ ] **Phase 2: Security & Robustness** — 安全加固与鲁棒性提升（3 项 TECHD）
- [ ] **Phase 3: Modularization** — 模块拆分与文档补充（3 项 TECHD）

---

## Phase Details

### Phase 1: Foundation
**Goal:** 所有脚本文件编码统一为 UTF-8 with BOM，换行符标准化，路径管理集中化，基础设施制度化
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** TECHD-01, TECHD-02, TECHD-03, TECHD-04, TECHD-05

**Success Criteria** (what must be TRUE):
1. 所有 7 个 UTF-16LE .ps1 文件编码统一为 UTF-8 with BOM，`file` 命令确认文件类型为 "UTF-8 Unicode (with BOM)"，`git diff` 可正确显示文本变更而非 "binary files differ"
2. 所有 `.sh` 文件换行符为 LF（`grep -rl $'\r$' --include='*.sh'` 返回空），Shell 脚本在 WSL/Linux/macOS 上可直接执行无 "No such file or directory" 报错
3. `.claude/harness/` 下所有 .ps1 文件中损坏的中文注释恢复为可读中文，无乱码残留
4. `.claude/state/` 成为 `features.json` 的唯一标准路径，旧 `.claude/harness/features.json` 双重查找逻辑从所有 8 个相关脚本中移除
5. `templates/state/` 目录清理完毕：多余 JSON 文件移除或合并，剩余模板的角色和用途在注释中明确标注
6. `.gitattributes` 和 `.editorconfig` 文件存在于仓库根目录，自动约束 .sh/.ps1/.py/.json/.md 等文件类型的换行符和编码
7. 全语言回归验证通过：分别创建 C++/Qt、Rust、Python 三种语言目标工程，运行完整 Setup→Plan→Implement→Review→Verify 流程，确认编码/换行符/路径修改未破坏任何语言工作流

**Plans:** 5 plans in 3 waves

**Plan list:**
- [ ] 01-01-ps-encoding-PLAN.md — PS 脚本 UTF-16LE → UTF-8 with BOM + 中文注释修复
- [ ] 01-02-shell-line-endings-PLAN.md — Shell 脚本 CRLF → LF 换行符修复
- [ ] 01-03-features-json-path-PLAN.md — 统一 features.json 路径为 .claude/state/
- [ ] 01-04-templates-state-cleanup-PLAN.md — 清理 templates/state/ + 修复 init-project.ps1
- [ ] 01-05-gitattributes-editorconfig-PLAN.md — 添加基础设施配置文件

---

### Phase 2: Security & Robustness
**Goal:** 消除命令注入风险、JSON 解析脆弱性和格式化性能问题
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** TECHD-07, TECHD-08, TECHD-09

**Success Criteria** (what must be TRUE):
1. PSScriptAnalyzer 对所有脚本执行时报告零个 `AvoidUsingInvokeExpression` 警告 — `run-regression.ps1` 中的全部 `Invoke-Expression` 已替换为 `&` 调用运算符或 `Start-Process` + `-ArgumentList`
2. 所有 Hook 脚本（`clang-format.ps1`、`pre-tool-use.ps1` 及对应的 `.sh` 版本）使用 `ConvertFrom-Json`（PowerShell）或 `jq`/Python（Shell）解析 JSON 输入，无任何 `-notmatch`/`sed` 正则提取 JSON 字段的代码，且"失败不阻塞"语义（`exit 0` on error）保持完整
3. `format-all.py` 的 `format_rust` 函数仅执行一次 `cargo fmt`（移除无用的 `--check`），且 `Cargo.toml` 目录查找结果被缓存，同一会话中多次写入 Rust 文件不会触发重复目录遍历
4. 全语言回归验证通过：Hook 脚本的安全修复不破坏格式化和编码转换行为，C++/Qt、Rust、Python 三种语言目标工程中 PostToolUse 格式化正常工作

**Plans:** TBD

---

### Phase 3: Modularization
**Goal:** 脚本模块化拆分、配置路径灵活化、知识文档化
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** TECHD-06, TECHD-10, TECHD-11

**Success Criteria** (what must be TRUE):
1. `update-progress.ps1` 拆分为 5 个领域模块 + 1 个薄编排器：`validate-transition.ps1`、`oracle-runner.ps1`、`report-generator.ps1`、`progress-logger.ps1`、`git-helper.ps1`，每个模块职责单一且不超过 150 行，编排器不超过 50 行，状态机核心契约（5 状态矩阵、`depends_on` DAG 检查、Oracle 验证）保持不变
2. `init-project.ps1` 中硬编码的 `$env:USERPROFILE\.claude\skills\harness-cc` 路径已替换为 `$PSScriptRoot` 相对路径或 `$env:CLAUDE_PLUGIN_ROOT`，在自定义安装路径下仍能正确定位技能源文件
3. 缺失文档补充完成，包含以下三个章节：(a) 编码策略说明 — UTF-8 with BOM 选择理由、PowerShell 编码陷阱、显式 `-Encoding utf8` 原则；(b) JSON 模板角色文档 — `templates/state/` 下每个模板的用途、安装目标、与 `features.json` 的关系；(c) Hook 调试指南 — 如何启用 `HARNESS_DEBUG` 模式、手动运行 Hook 脚本的命令、日志文件位置
4. 全语言回归验证通过：C++/Qt、Rust、Python 三种语言目标工程分别运行完整 Setup→Plan→Implement→Review→Verify 流程，确认模块拆分和路径修复未破坏任何工作流环节
5. 全 6 种语言（C++/Qt、C++/CMake、Python、Node.js、Rust、Go）的目标工程验证初始化流程，确认 `init-project.ps1` 能正确定位技能源文件并完成项目初始化

**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/0 | Not started | - |
| 2. Security & Robustness | 0/0 | Not started | - |
| 3. Modularization | 0/0 | Not started | - |

---

## Dependencies

```
Phase 1 (Foundation)          Phase 2 (Security)          Phase 3 (Modularization)
   编码统一 ────────────→   安全加固 ────────────→   模块拆分
   换行符修复               JSON 解析修复              路径修复
   路径标准化               性能修复                   文档补充
   基础设施制度化           （依赖可读文件）            （依赖已安全代码）
```

**关键依赖说明：**
- Phase 1 必须先于 Phase 2：编码统一前文件不是 UTF-8，Git diff 无法正确显示后续变更，安全修复无法审查
- Phase 2 必须先于 Phase 3：脚本拆分前必须先替换不安全代码（`Invoke-Expression`、正则解析），否则拆分后安全问题的排查范围会扩大 5 倍
- 禁止在编码修复和代码修复之间反复切换：每次编码转换会使之前的 diff 变得不可阅读

---

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| TECHD-01 | Phase 1 | Pending |
| TECHD-02 | Phase 1 | Pending |
| TECHD-03 | Phase 1 | Pending |
| TECHD-04 | Phase 1 | Pending |
| TECHD-05 | Phase 1 | Pending |
| TECHD-07 | Phase 2 | Pending |
| TECHD-08 | Phase 2 | Pending |
| TECHD-09 | Phase 2 | Pending |
| TECHD-06 | Phase 3 | Pending |
| TECHD-10 | Phase 3 | Pending |
| TECHD-11 | Phase 3 | Pending |

**v1 requirements:** 11 total
**Mapped to phases:** 11
**Unmapped:** 0
**Coverage:** 100% ✓
