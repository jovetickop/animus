# Requirements: ty-qt-ai-plugin (harness-cc)

**Defined:** 2026-06-14
**Core Value:** 让 AI 辅助的编码工作可跟踪、可验证、可重复

## v1 Requirements

技术债务修复，按阶段分组。

### Foundation — 编码与基础设施统一

- [ ] **TECHD-01**: 将 7 个 UTF-16LE .ps1 文件统一为 UTF-8 with BOM 编码（`templates/harness/` 下 4 个 + `commands/` 下 3 个）
- [ ] **TECHD-02**: 修复 `.sh` 文件换行符 CRLF → LF（`hooks/scripts/` 下 4 个）
- [ ] **TECHD-03**: 修复已损坏的中文注释（UTF-16LE 文件中不可读的中文字符串）
- [ ] **TECHD-04**: 统一 `features.json` 标准路径为 `.claude/state/`，消除双重查找逻辑（涉及 8 个脚本）
- [ ] **TECHD-05**: 清理 `templates/state/` 目录，明确 3 个 JSON 模板的角色和用途
- [ ] **TECHD-11(部分)**: 添加 `.gitattributes` 和 `.editorconfig` 文件作为制度性保障

### Security & Robustness — 安全加固与鲁棒性提升

- [ ] **TECHD-07**: 替换 `run-regression.ps1` 中的 `Invoke-Expression` 为安全的 `Start-Process` 或 `&` 调用
- [ ] **TECHD-08**: 修复 Hooks 脚本中正则解析 JSON 为 `ConvertFrom-Json`（`clang-format.ps1`、`pre-tool-use.ps1`）
- [ ] **TECHD-09**: 修复 `format-all.py` 中 Rust 双重 `cargo fmt`（移除无用的 `--check`）+ 缓存 `Cargo.toml` 目录查找

### Modularization — 模块拆分与文档补充

- [ ] **TECHD-06**: 拆分 `update-progress.ps1`（424 行 → 5 个领域模块：validate-transition / oracle-runner / report-generator / progress-logger / git-helper）
- [ ] **TECHD-10**: 修复 `init-project.ps1` 中硬编码的用户技能路径
- [ ] **TECHD-11**: 补充编码策略说明、模板角色文档、钩子调试方式等缺失文档

## v2 Requirements

- **TECHD-12**: 创建 `scripts/shared/resolver.py` + `path-resolver.ps1` 共享路径查找模块（如 Phase 1 临时修复后仍需集中化）
- **TECHD-13**: 重构 `hooks.json` 错误处理，添加调试日志而非静默降级
- **TECHD-14**: 为 `format-all.py` 添加第三方格式化工具是否安装的前置检查

## Out of Scope

| Feature | Reason |
|---------|--------|
| 新增语言支持（Swift/Kotlin/Java） | 不是技术债务范畴 |
| 新增功能特性 | 本次专注于修复而非新功能开发 |
| 重构状态机引擎为其他语言 | 保持现有 PowerShell 实现 |
| 修改 `features.json` 字段契约 | 必须保持向后兼容 |
| reviewdog rdjson 输出格式 | 属于新功能，非债务修复 |
| 异步 PostToolUse 日志 | 属于新功能，非债务修复 |

## Traceability

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

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-14*
*Last updated: 2026-06-14 after roadmap creation*
