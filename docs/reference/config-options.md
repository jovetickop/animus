---
type: reference
audience: regular-user
---

# 配置参考

> Animus 全部配置项说明 — `.claude/animus/config.json`。
> 两层覆盖：硬编码默认值 ← `config.json`（只写需要覆盖的项即可）。

---

## `[project]` — 项目信息

由 `/animus-init` 自动检测填入。

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `type` | string | `"generic"` | 项目类型（cpp-qt / cpp-cmake / rust / go / node / python / generic） |
| `build_command` | string | `""` | 构建命令（留空表示无标准构建） |
| `test_command` | string | `""` | 测试命令 |
| `run_command` | string | `""` | 运行命令 |
| `auto_update_plugin` | bool | `true` | 启动时自动检查插件更新 |

---

## `[project.verify]` — Oracle 验证门控

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `command` | string | `""` | 验证命令（如 `cmake --build build`） |
| `enabled` | bool | `false` | 是否启用验证门控 |
| `timeout_seconds` | int | `120` | 验证命令超时时间（秒） |

---

## `[dev]` — 开发行为

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `default_path` | string | `"auto"` | AI 自动检测时的路径倾向：`auto` / `fast` / `light` / `full` |
| `autonomous` | bool | `false` | 自主模式：`true`=AI 全权决策不询问，`false`=每次确认 |

---

## `[review]` — 代码审查

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `strictness` | string | `"normal"` | 审查严格度：`low`（仅 HIGH）/ `normal`（HIGH+MEDIUM）/ `high`（全部） |
| `skip_categories` | array | `[]` | 跳过的审查类别：`naming` / `formatting` / `performance` / `security` |
| `max_findings` | int | `20` | 每次审查最多输出多少条问题（推荐 15-30） |

---

## `[gates]` — 门控规则

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `require_task_before_write` | bool | `true` | 写代码前必须有 in_progress 任务，否则 PreToolUse 拦截 |

---

## `[ponytail]` — 精简审查

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `enabled` | bool | `true` | 启用 Ponytail 精简审查（检查过度工程、冗余抽象、死代码） |
| `max_lines_per_file` | int | `500` | 文件超过此行数建议拆分（0=不限制） |

---

## `[party_mode]` — 辩论模式

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `default_mode` | string | `"subagent"` | 运行模式：`session` / `subagent` / `auto` / `agent-team` |
| `default_party` | string | `"arch-review"` | 默认模板：`arch-review` / `code-review` |
| `auto_trigger` | array | `["dev-full", "review-controversial"]` | 自动触发场景 |
| `ask_before_start` | bool | `true` | 触发前询问用户 |
| `max_rounds` | int | `3` | 最大辩论轮数（1-3 快速收敛，5+ 深度讨论） |
| `memory_enabled` | bool | `true` | 是否启用辩论历史记忆 |

---

## 示例：最小配置

```toml
[project]
type = "cpp-qt"
build_command = "cmake --build build"
test_command = "ctest --test-dir build"

[dev]
autonomous = true
```

## 示例：完整配置

```toml
[project]
type = "rust"
build_command = "cargo build"
test_command = "cargo test"
run_command = "cargo run"
auto_update_plugin = true

[project.verify]
command = "cargo test --lib"
enabled = true
timeout_seconds = 180

[dev]
default_path = "auto"
autonomous = false

[review]
strictness = "high"
skip_categories = ["formatting"]
max_findings = 30

[gates]
require_task_before_write = true

[ponytail]
enabled = true
max_lines_per_file = 800

[party_mode]
default_mode = "subagent"
default_party = "arch-review"
auto_trigger = ["dev-full"]
ask_before_start = true
max_rounds = 3
memory_enabled = true
```
