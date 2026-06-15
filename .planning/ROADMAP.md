# Roadmap: ty-qt-ai-plugin (harness-cc)

**Core Value:** 让 AI 辅助的编码工作可跟踪、可验证、可重复
**Milestone:** v1.0 技术债务修复 — 11 项 TECHD 项
**Granularity:** Coarse (single phase, 已完成 + 1 个剩余阶段)
**Created:** 2026-06-14
**Simplified:** 2026-06-15 — 合并为单阶段执行

---

## 阶段概览

简化策略：借鉴 GSD 但避免过度拆分。已完成部分作为历史记录，剩余 6 项 TECHD 合并为单一阶段"修复与文档"。

---

## Phase 1: 技术债务修复（合并）

**Goal:** 完成所有 11 项 TECHD 修复 — 编码统一、路径标准化、安全加固、模块化、文档化

**Status:** 部分完成（5/11 项已修复并推送），剩余 6 项在本次阶段完成

### ✅ 已完成（Phase 1: Foundation — 2026-06-14）

- ✅ **TECHD-01**: 7 个 UTF-16LE .ps1 文件统一为 UTF-8 with BOM（commit 38b38cf）
- ✅ **TECHD-02**: 3 个 .sh 文件 CRLF → LF（commit 56030ae）
- ✅ **TECHD-03**: 中文字符编码已自动恢复（编码转换过程中）
- ✅ **TECHD-04**: features.json 路径标准化为 `.claude/state/`（commit 13fff41）
- ✅ **TECHD-05**: `templates/state/` 清理 + 修复 init-project.ps1 源路径（commit 3e45e28）
- ✅ **TECHD-11(部分)**: `.gitattributes` + `.editorconfig`（commit 45d29c3）

### ⏳ 待执行（Phase 2-3 合并为单阶段）

- ⏳ **TECHD-07**: 替换 `Invoke-Expression` 为安全的 `Start-Process` / `&` 调用
- ⏳ **TECHD-08**: 修复 Hook 脚本正则解析 JSON 为 `ConvertFrom-Json`
- ⏳ **TECHD-09**: 修复 `format-all.py` 双重 `cargo fmt` + 缓存 `Cargo.toml` 查找
- ⏳ **TECHD-06**: 拆分 `update-progress.ps1`（424 行 → 5 个领域模块）
- ⏳ **TECHD-10**: 修复 `init-project.ps1` 硬编码用户技能路径
- ⏳ **TECHD-11**: 补充编码策略、模板角色、钩子调试等缺失文档

---

## 简化原则

**借鉴 GSD 但避免过度工程：**
- ✅ 保留：目标倒推、原子提交、依赖驱动 Wave、中文提交记录、独立子 Agent
- ❌ 简化：3 阶段拆分、强制多 Agent 编排、强制 Nyquist 验证、固定阶段门控

**执行节奏：**
1. 一次规划完成剩余 6 项
2. Wave 内并行执行
3. 每完成一个 Plan 立即提交 + 推送
4. 最后做一次全语言回归 + skill-creator 评估

---

*Last updated: 2026-06-15 — 阶段合并简化*
