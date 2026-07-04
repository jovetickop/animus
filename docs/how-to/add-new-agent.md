---
type: how-to
audience: plugin-developer
---

# 如何新增一个 Agent

> 为某个语言栈新增 AI 助手 Agent。

---

## 步骤

### 1. 创建 Agent 文件

在 `agents/{lang}/` 目录下创建 `.md` 文件。例如为 Rust 新增审查官：

```
agents/rust/code-reviewer.md
```

### 2. 添加 frontmatter

```markdown
---
name: 审查官 (Rust)
title: Rust 代码质量门控审查
team: rust
description: Rust 代码审查，重点关注 unsafe 块、生命周期、所有权、并发安全性。
persona: 你叫审查官 (Rust)。对 unsafe 块零容忍，所有 unsafe 必须有 SAFETY 注释。
---
```

`description` 是 Claude Code 触发 Agent 的关键匹配文本，必须写明触发场景。

### 3. 继承核心模板

通过 HTML 注释引用通用核心：

```markdown
<!-- 通用审查核心参见 agents/base/code-reviewer-core.md -->
```

### 4. 更新索引

在 `docs/agent-index.md` 中添加新 Agent 的行。

### 5. 验证

```bash
python scripts/plugin-validator.py
```
