# Feature Landscape: Claude Code Skill — Multi-Language Code Review Orchestration

**Domain:** AI-assisted code review orchestration framework (Claude Code skill plugin)
**Researched:** 2026-06-14
**Confidence:** HIGH (convergent findings across multiple production tools)

## Executive Summary

This document maps the feature landscape for `harness-cc`, a Claude Code skill that orchestrates multi-language code formatting, linting, review, and state-machine-driven development workflows. The research surveyed four domains: multi-language formatting pipelines, state machine progress tracking, Claude Code skill ecosystem conventions, and cross-platform hook/integration systems.

**Key finding:** The existing harness-cc implementation already covers most table-stakes features. The gaps lie in reliability (encoding uniformity, JSON parsing robustness, modularity) and ergonomics (documentation, debugging support, gradual rollout). The differentiators — encoding bridge (GBK/UTF-8), Python 2/3 dual compatibility, multi-agent per-language specialization, Oracle verification — are what justify the skill's existence.

---

## Feature Landscape — Domain Breakdown

---

### Domain 1: Multi-Language Code Formatting & Linting Pipeline

Research sources: [MegaLinter](https://megalinter.io/) (production: 69+ languages, 100+ linters), [linthis](https://pypi.org/project/linthis/) (parallel + cache), [pre-commit](https://pre-commit.com/) (Python ecosystem), [Lefthook](https://github.com/evilmartians/lefthook) (parallel, polyglot), [husky](https://typicode.github.io/husky/) (JS ecosystem).

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Auto-format on file write | Users expect every edit to be formatted automatically without manual steps | LOW | Claude Code PostToolUse hook — already implemented as `clang-format.ps1/.sh` + `format-all.py` |
| Language-specific formatter detection | Each language has canonical formatters (black, prettier, cargo fmt, clang-format); user should not configure manually | MEDIUM | Already implemented in `format-all.py` with priority-based fallback (black → autopep8, prettier → eslint --fix) |
| Format-only changed files | In large repos, formatting unchanged files wastes time | MEDIUM | PostToolUse hook receives `$CLAUDE_TOOL_INPUT_FILE_PATH` — already scoped to edited files |
| Graceful failure on missing formatter | Missing tool should warn but not block workflow | LOW | Already implemented: `except Exception: return False` in format-all.py |
| CI-compatible format checking | Must provide `--check` mode for CI pipelines (e.g., `cargo fmt --check`, `black --check`) | LOW | Not yet exposed as a user-triggerable command — only runs on Write/Edit via hook |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Encoding-aware formatting bridge (GBK <-> UTF-8) | Chinese Windows C/C++ projects use GBK encoding; tools expect UTF-8. Encoding bridge silently converts bidirectionally inside hooks | HIGH | Already implemented as `encoding-bridge.py` in PreToolUse/PostToolUse — this is a rare feature not found in MegaLinter, pre-commit, or any competitor |
| Python 2/3 dual-compatible formatter runner | Target projects may still use Python 2 (common in legacy Chinese industrial environments). Runner must not introduce dependency on Python 3 | MEDIUM | Already implemented: uses `from __future__` imports, `subprocess.Popen` + `communicate()` pattern |
| Multi-language unified format runner (`format-all.py`) | Single entry point routing to language-specific formatters, rather than per-language hook scripts | MEDIUM | Already implemented — dispatches to black/autopep8/prettier/eslint/cargo fmt by file extension |
| Format-result caching per workspace | Avoid re-running `cargo fmt` on every write by caching Cargo.toml discovery | LOW | Bug TECHD-09 identified duplicate `cargo fmt` runs — caching fix is low complexity and high value |
| Formatter presets per project type | Different project types (Qt Widgets vs Qt Quick vs pure C++) should auto-select appropriate `.clang-format` | MEDIUM | Not implemented — currently ships a single `.clang-format` template; project-config.json `type` field exists but not wired to formatting config |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Bundling 50+ linters (like MegaLinter) | "Cover all languages" sounds comprehensive | 1) Token cost in skill distribution; 2) Installation overhead; 3) Most formatters never used. MegaLinter does this with Docker images (100+ linters); a skill plugin should not | Support discovery of locally installed formatters — use what's in PATH, don't ship formatters with the skill |
| Blocking workflow on format errors | "Code must be clean" seems disciplined | 1) Hook must fail non-blocking per Claude Code contract (`exit 0`); 2) Blocks iterative development | Report format issues via `additionalContext` in PostToolUse, let user decide when to fix |
| Running ALL formatters on EVERY file write | "Be thorough" | Unnecessary overhead for single-file edits. `cargo fmt` on a Rust project with 50 files re-formatting everything on a single `.rs` change is wasteful | Scope to the single edited file unless the formatter requires project-level context (which is the exception, not the rule) |
| Custom linter/formatting rule DSL | "Need per-team rules" | Creates a new configuration language users must learn. Community tools (`.clang-format`, `.prettierrc`, `pyproject.toml`) already exist with mature tooling | Delegate to existing config files; use `project-config.json` to reference them, not replace them |

---

### Domain 2: State Machine / Progress Tracking for Development Workflows

Research sources: [task-orchestrator-py](https://pypi.org/project/task-orchestrator-py/) (MCP server, `queue → work → review → done`), [Monoco Toolkit](https://pypi.org/project/monoco-toolkit/) (Issue as Code + Kanban), [LoopForge](https://pypi.org/project/loopforge/) (CI/CD lifecycle state machine), [OpenHorizon Workflows](https://www.npmjs.com/package/@openhorizon/workflows) (agent pipelines), [YouTrack state machine workflows](https://jetbrains.com) (guards, on-enter actions).

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| State transitions with validation | Users must not be able to skip steps (e.g., mark as done without running tests) | HIGH | Already implemented — `update-progress.ps1` enforces `pending→in_progress→passed/failed` with `failed→in_progress` retry |
| Dependency tracking (`depends_on`) | Tasks often depend on predecessors; the system should block unordered execution | MEDIUM | Already implemented — `depends_on` field in `features.json`; script rejects transition if dependencies not passed |
| Single active task enforcement | Prevents chaos of parallel partial work | MEDIUM | Already implemented — script allows only one `in_progress` at a time |
| Progress log / audit trail | Every transition must be recorded for debugging and accountability | LOW | Already implemented — `claude-progress.txt` append + `docs/reports/<TaskId>-<name>.md` generation |
| Feature JSON schema for task structure | Users need to know the expected fields and their types | LOW | Already present as `features.json` with fields: id, name, status, depends_on, priority, test_command, last_error, updated_at, acceptance_criteria |
| Session resume / recovery | After session timeout or crash, system restore state so user does not lose progress | MEDIUM | Partially implemented — `session-catchup.py` reads features.json; Stop hook produces recovery hints. Missing: explicit `/resume` skill command |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Oracle verification (build + test evidence required) | Unlike simple Kanban boards, harness-cc enforces that `in_progress → passed` requires successful build AND test execution. This prevents "I'll test later" gaps | HIGH | Already implemented — `update-progress.ps1` runs `test_command` and validates exit code before allowing `passed` |
| Git auto-commit on state transition | Each `passed` state transition automatically commits changes with a formatted message, creating a fully traceable git history | LOW | Already implemented — script runs `git add` + `git commit` after successful transition |
| Multi-language build tool detection | Auto-detect CMake, Cargo, Go, npm, pip from project files; configure build/test commands without manual setup | MEDIUM | Already implemented in `harness-code-setup.ps1` — detects 6 project types |
| Integration with Claude Code session lifecycle | Stop hook generates recovery instructions; PreCompact hook persists state before context compression; hooks integrate with the AI lifecycle, not just git lifecycle | HIGH | Already implemented — all four Claude Code hook types (PreToolUse, PostToolUse, PreCompact, Stop) are wired |
| Parallel task groups (`parallel_group` field) | Tasks within a group can be worked on in any order; only cross-group dependencies enforce ordering | MEDIUM | Already supported in `features.active.json` template via `parallel_group` field — though not yet used by core scripts |
| Report generation per state transition | Markdown reports with task id, status, timestamp, error output created automatically | LOW | Already implemented — `docs/reports/<TaskId>-<name>.md` generation on each transition |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Visual state machine editor / UI | "Makes state machines accessible" | 1) Claude Code is a CLI tool — a GUI is out of scope; 2) Would need Electron/web stack dependency; 3) not what users expect from a skill plugin | Use `features.json` as the source of truth; provide `validate-features.ps1` to validate JSON integrity |
| Real-time multi-user collaboration | "Team can see progress live" | 1) Requires server infrastructure; 2) Skill plugins are per-user by design; 3) Conflict resolution complexity | Git remains the collaboration layer — each dev has their own features.json; merge via Git |
| Pushing state to Jira/Linear automatically | "Always sync with PM tools" | 1) One-way sync is easy but debuggable mismatches are damaging; 2) Two-way sync is extremely complex | Keep MCP integration (Linear already configured) as optional user-triggered sync, not auto-sync |
| Complex workflow branching | "Need different paths for different task types" | 1) Increases state machine complexity exponentially; 2) Debugging becomes non-linear | Keep one canonical flow; if different paths are needed, use separate `features.json` instances per context |

---

### Domain 3: AI Agent Skill Plugins (Claude Code Skills Ecosystem)

Research sources: [Claude Code Skills Marketplace](https://skywork.ai/blog/ai-bot/claude-code-skills-marketplace-ultimate-guide/) (2026), [claude-code-extensions](https://github.com/nodnarbnitram/claude-code-extensions) (18 skills/21 plugins/60+ agents), [claude-skills by alirezarezvani](https://github.com/alirezarezvani/claude-skills) (338 skills), [Anthropic hook documentation](https://claude.com/blog/how-to-configure-hooks), [anipotts/claude-code-tips](https://github.com/anipotts/claude-code-tips) (production patterns).

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `SKILL.md` with YAML frontmatter | Required for Claude Code skill discovery — defines name, description, activation context | LOW | Already implemented — frontmatter includes name, description, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `context: fork` |
| Slash commands (3+ commands) | Users discover features via `/command` in Claude Code chat | LOW | Already implemented — `/harness-code-setup`, `/harness-code-plan`, `/harness-code-review` |
| Progressive disclosure | Skill instructions load lazily (30-50 tokens per skill), not all at once | — | This is a platform feature, not skill-level. Skill files are loaded by Claude Code core, not implemented by the skill author |
| Agent definitions per domain | Domain-specific AI agents (architect, implementer, reviewer, tester) that Claude dispatches to based on task | MEDIUM | Already implemented — 23 agents across 6 languages + universal roles |
| Coding rules / conventions | Language-specific coding standards that agents follow when writing or reviewing code | LOW | Already implemented — 12 rule files in `.claude/rules/` covering universal, Qt, C++, Python, Node.js, Rust, Go, frontend |
| Hook integration for workflow automation | Deterministic enforcement (auto-format, state save, stop hooks) that runs regardless of model behavior | MEDIUM | Already implemented — 4 hook types, dual bash+PowerShell implementation |
| Project type auto-detection | Skill must recognize project type (Cargo, CMake, npm, pip, Go) and adapt behavior | MEDIUM | Already implemented — language detection via file existence checks in `harness-code-setup.ps1` |
| MCP server integration | Filesystem, Git, Memory, and issue tracking MCP servers for external tool access | MEDIUM | Already implemented — filesystem, git, memory, Linear configured in `.mcp.json` |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-language agent specialization | Separate agent personas per language (Qt architect, Rust reviewer, Python tester) — not just language-agnostic "code review" | HIGH | Already implemented — 6 language-specific agent teams. Most Claude Code skills are single-language or language-agnostic |
| Encoding bridge for Chinese projects | GBK <-> UTF-8 transparent conversion inside hooks. Critical for Chinese Windows C++ teams where GBK is the default | HIGH | Already implemented — `encoding-bridge.py`. No competitor skill in the Claude Code ecosystem does this |
| State machine as skill orchestration | Not just a Kanban viewer — a full state machine with oracle verification, dependency tracking, and AI lifecyle integration | HIGH | Already implemented — distinct from simpler task trackers like Monoco's `Proposed→Done` linear flow |
| Installation as a single command | `/harness-cc` detects project type, copies templates, configures hooks, initializes features.json, configures MCP — all in one flow | MEDIUM | Already implemented — `init-project.ps1` performs all of these in a single invocation |
| Session resilience (hooks write progress before compaction) | PreCompact hook persists work before context compression; Stop hook generates recovery instructions | MEDIUM | Already implemented — `pre-compact.ps1/.sh` and `stop-check.ps1/.sh` |
| Skill is also a published plugin | Can be distributed through Claude Code plugin marketplace (`marketplace.json` format) | LOW | Not yet packaged as a marketplace plugin — currently installed via manual script copy. Publishing to a marketplace would improve discoverability |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Replacing human code review entirely | "Let AI do all the reviewing" | 1) Spurious issues waste reviewer time; 2) Subtle logic bugs escape AI review; 3) Team knowledge transfer is lost | AI review as *first pass* — flag suspicious patterns, triage, then human decides |
| Self-modifying skill installation | "Skill should update itself" | 1) Security risk — prompt injection to modify core files; 2) Version tracking becomes impossible | Manual upgrade flow: `harness-code-setup` with explicit version flag; user decides when to upgrade |
| 50+ agent definitions for every niche scenario | "More agents = more coverage" | 1) Agent discovery degrades with too many choices; 2) Token overhead (each agent definition loads on session start); 3) Maintenance burden | Keep agent definitions to high-coverage roles (architect, implementer, tester, reviewer) per supported language; extend only when pain point is validated |
| Skill trying to manage external CI/CD | "Run GitHub Actions from the skill" | 1) CI tokens exposed in session; 2) Claude Code session is ephemeral — long-running CI is out of scope; 3) Duplicates existing CI tooling | Keep CI integration at the `features.json` command level — let the skill run local validation; CI runs independently |

---

### Domain 4: Cross-Platform Hook / Integration Systems for Developer Tools

Research sources: [Claude Code hooks official docs](https://claude.com/blog/how-to-configure-hooks), [anipotts/claude-code-tips hooks patterns](https://github.com/anipotts/claude-code-tips), [Lefthook](https://github.com/evilmartians/lefthook) (parallel cross-platform), [pre-commit](https://pre-commit.com/) (multi-language), [Husky/Js](https://typicode.github.io/husky/), [megalinter](https://megalinter.io/) (CI-focused hooks), [Claude Code issue #32407](https://github.com/anthropics/claude-code/issues/32407) (power user patterns).

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| PreToolUse hook | Runs before tool execution — allows validation or modification | MEDIUM | Already implemented — `pre-tool-use.ps1/.sh` backs up features.json + GBK→UTF-8 conversion |
| PostToolUse hook | Runs after tool success — auto-format, logging | MEDIUM | Already implemented — `clang-format.ps1/.sh` + `format-all.py` for multi-language formatting + UTF-8→GBK conversion |
| Stop hook | Runs at session end — save state, generate recovery hints | MEDIUM | Already implemented — `stop-check.ps1/.sh` checks for incomplete tasks, outputs resume instructions |
| PreCompact hook | Runs before context compression — persist state that would otherwise be lost | MEDIUM | Already implemented — `pre-compact.ps1/.sh` writes progress to `claude-progress.txt` |
| Non-blocking failure semantics | Hook failures must not crash the Claude Code session (platform contract) | LOW | Already implemented — `|| exit 0` ensures graceful degradation |
| Cross-platform support (Windows + Unix) | Hooks must work on Windows (PowerShell) and Unix (Bash) | MEDIUM | Already implemented — dual `ps1` + `sh` implementations for every hook |
| Hook timeout handling | Long hooks should not hang the session indefinitely | LOW | Already implemented — `timeout: 10` in `hooks.json` |
| SessionStart context loading | Inject project context (git status, pending tasks) at session start | LOW | Not implemented — current setup relies on user or Claude reading CLAUDE.md manually |
| Notification hooks | Desktop notifications for long-running operations | LOW | Not implemented — lower priority; Claude Code CLI has built-in terminal audio cues |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Encoding bridge baked into hooks | PreToolUse (GBK→UTF-8) + PostToolUse (UTF-8→GBK) bidirectional encoding conversion inside the write pipeline. No other Claude Code skill does this | HIGH | Already implemented — `encoding-bridge.py` integrated into both pre-tool-use and clang-format hooks |
| Dual-language hook implementation with fallback | `bash ... || powershell ... || exit 0` — script runs on any platform without requiring specific shell | MEDIUM | Already implemented — `hooks.json` registers both bash and PowerShell with `||` fallback |
| JSON parsing improvements (ConvertFrom-Json over regex) | Parsing hook input JSON with structured parser instead of fragile regex `-notmatch` patterns | LOW | Bug TECHD-08 identified regex parsing in `clang-format.ps1` and `pre-tool-use.ps1` — fix target |
| Parallel hook execution via `hooks.json` `"async": true` | Async hooks add zero latency to user-facing operations (logging, cost tracking) | MEDIUM | Not implemented — all hooks are currently synchronous; async logging for audit trail could be added |
| Statusline integration for shared state | Statusline command writes current model, effort level to `/tmp/` for hook context-awareness | LOW | Not implemented — could help hooks adapt behavior based on model tier or effort level |
| Hook debugging mode (verbose flag) | When hooks fail, user needs to see what happened — current `/dev/null` redirection swallows errors | LOW | Bug TECHD-11 identified missing debug documentation — adding a `--verbose` or environment-flag mode would help |
| Permission model layering | `permissions.deny` (absolute) + PreToolUse (pattern) + sandbox (filesystem) defense in depth | MEDIUM | Partially implemented — `settings.local.json` configures permissions; sandbox mode needs more deliberate configuration |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Single script handling ALL hook events | "Easier to maintain one file" | 1) Violates single-responsibility; 2) Hard to debug; 3) Changes to one event risk breaking others | Keep per-event scripts (pre-tool-use, clang-format, pre-compact, stop-check) — already implemented correctly |
| Blocking work on hook failure | "Hooks must guarantee quality" | 1) Claude Code contract requires non-blocking hooks; 2) Flaky formatting tools would block all edits | Fail-open (`exit 0`), surface errors in PostToolUse `additionalContext` — already implemented |
| Centralized hook management server | "Team should share hook policies" | 1) Requires server; 2) Single point of failure; 3) Offline development breaks | Use `project-config.json` as the policy file — checked into Git, shared via normal Git workflow |
| Hook auto-update from remote URL | "Always run latest hooks" | 1) Security — URL could be hijacked; 2) Unpredictable behavior changes mid-session | Version hooks with the skill plugin; user runs `harness-code-setup` to upgrade explicitly |
| Ten different hook types | "Maximum automation surface" | 1) Each hook type adds complexity; 2) Most users only need 3-4; 3) Claude Code only supports 8 events, and not all are equally useful | Focus on the high-value hook points: PostToolUse (format), PreCompact (save), Stop (resume), PreToolUse (guard) |
| Monitoring hooks via external dashboard | "See what hooks are doing in real time" | Far outside the scope of a Claude Code skill plugin. Would require server infrastructure, WebSocket, auth | Use local logging (append to `claude-progress.txt`) — already implemented; inspect via `git log` or terminal |

---

## Feature Dependencies

```
PostToolUse formatting ──requires──> Language-specific formatter detection
    └──enhances──> Encoding bridge (GBK↔UTF-8)

State machine transitions ──requires──> features.json schema
    └──requires──> Oracle verification (build/test commands)
    └──enhances──> Git auto-commit on transition

Session resume ──requires──> PreCompact hook (persist state)
    └──requires──> Stop hook (generate recovery hints)

Project setup ──requires──> Project type detection
    └──requires──> Template copying (features.json, project-config.json, .clang-format, .mcp.json)
    └──enhances──> MCP server configuration

Agent dispatch ──requires──> Agent definitions per language
    └──requires──> Coding rules per language
    └──enhances──> Language-specific review checklist

Skill activation ──requires──> SKILL.md with YAML frontmatter
    └──requires──> CLAUDE.md with skill reference

Encoding bridge ──requires──> PreToolUse hook (GBK→UTF-8 read)
    └──requires──> PostToolUse hook (UTF-8→GBK write)
```

### Dependency Notes

- **Encoding bridge requires both hooks:** Without PreToolUse conversion, the AI sees garbled Chinese characters. Without PostToolUse conversion, the file is saved as UTF-8 but the project expects GBK. Both directions are needed for correct round-trip.
- **State machine requires features.json schema:** The schema fields (depends_on, status, test_command) are not optional — the state script parses them by position. Changing the schema requires updating all scripts that parse it.
- **Session resume requires PreCompact + Stop:** PreCompact saves state before compaction destroys it. Stop generates recovery instructions at session end. Together they form a safety net.
- **Agent dispatch requires both agent definitions and rules:** The agent (who) needs the rules (how) to produce correct output. Rules without agents are unused; agents without rules are unpredictable.

---

## MVP Definition

This is a brownfield project — the MVP is **already built and validated**. The current milestone is technical debt remediation, not feature addition. The following sections define the **minimum viable remediation scope**.

### Launch With (Tech Debt Fix v1)

The existing validated features ARE the MVP. For this remediation milestone:

- [ ] Unified script encoding: UTF-8 with BOM for all .ps1 files (TECHD-01)
- [ ] Fixed Shell script line endings: LF for all .sh files (TECHD-02)
- [ ] Repaired Chinese comments in formerly UTF-16LE scripts (TECHD-03)
- [ ] Standardized features.json path to `.claude/state/` (TECHD-04)
- [ ] Clarified three template JSON roles (TECHD-05)
- [ ] Modularized update-progress.ps1 (TECHD-06)
- [ ] Replaced Invoke-Expression with safe execution (TECHD-07)
- [ ] Fixed JSON regex parsing to ConvertFrom-Json (TECHD-08)
- [ ] Fixed format-all.py Rust formatting caching (TECHD-09)
- [ ] Fixed init-project.ps1 hardcoded user path (TECHD-10)
- [ ] Added missing documentation: encoding strategy, template roles, hook debugging (TECHD-11)

### Add After Validation (v1.x)

- [ ] Async PostToolUse logging for audit trail — adds zero latency to formatting pipeline
- [ ] `/resume` explicit command — wraps Stop hook output into a structured recovery flow
- [ ] `--verbose` flag for hooks — surfaces errors from `/dev/null` redirection for debugging
- [ ] `SessionStart` hook context injection — automatically loads git status and pending tasks at session start
- [ ] Marketplace plugin packaging — distribute through Claude Code plugin marketplace

### Future Consideration (v2+)

- [ ] Formatter presets per project type — wire `project-config.json` type field to `.clang-format` selection
- [ ] Statusline shared-state integration — model/effort awareness for hook adaptation
- [ ] `features.json` parallel group execution — wire existing `parallel_group` field into `update-progress.ps1`
- [ ] CI-compatible format checking command — expose `--check` mode as a user-invocable skill command

---

## Feature Prioritization Matrix

### For Tech Debt Remediation (Current Milestone)

| Feature (Tech Debt Item) | User Value | Implementation Cost | Priority |
|--------------------------|------------|---------------------|----------|
| TECHD-01: Unified script encoding | HIGH — fixes corrupt git diffs and garbled Chinese | MEDIUM — 7 files to convert with script, then verify | P1 |
| TECHD-02: Fix .sh line endings | MEDIUM — Shell scripts fail on Unix without LF | LOW — use `sed` or `dos2unix` | P1 |
| TECHD-03: Fix damaged Chinese comments | HIGH — current output is unreadable | MEDIUM — requires understanding intent from context | P1 |
| TECHD-04: Standardize features.json path | MEDIUM — reduces confusion and bugs | MEDIUM — update 7 scripts, test all paths | P1 |
| TECHD-05: Clarify template JSON roles | LOW — already works, just confusing | LOW — rename/comment files, add docs | P2 |
| TECHD-06: Modularize update-progress.ps1 | HIGH — 424-line script is hard to maintain | HIGH — careful refactor with regression tests | P2 |
| TECHD-07: Safe command execution | MEDIUM — security hardening | MEDIUM — replace Invoke-Expression, test all code paths | P2 |
| TECHD-08: JSON parsing robustness | MEDIUM — fragile regex breaks on complex JSON | LOW — replace with ConvertFrom-Json in 2 scripts | P1 |
| TECHD-09: Format-all.py Rust caching | LOW — wasted I/O but doesn't cause errors | LOW — add Cargo.toml caching, ~10 lines | P2 |
| TECHD-10: Fix hardcoded user path | MEDIUM — breaks non-default installations | LOW — use relative path or env var | P2 |
| TECHD-11: Missing documentation | MEDIUM — prevents future issues | MEDIUM — 3 doc sections to write | P2 |

### For New Feature Development (Post-Remediation)

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Async PostToolUse logging | LOW — nice to have | LOW — add `"async": true` + logger script | P3 |
| `/resume` command | MEDIUM — improves session recovery UX | MEDIUM — wrap Stop hook output into structured flow | P2 |
| Hook `--verbose` mode | MEDIUM — essential for debugging | LOW — add env var check in existing scripts | P2 |
| SessionStart context injection | HIGH — reduces manual context setup | MEDIUM — add hook script + config | P2 |
| Marketplace packaging | MEDIUM — improves discoverability | LOW — add marketplace.json + README | P2 |
| Formatter presets per project type | MEDIUM — better defaults for Qt vs C++ | MEDIUM — wire type field to config | P3 |
| CI format-check command | LOW — edge use case in skill context | LOW — expose existing tool in command | P3 |

---

## Competitor Feature Analysis

### Multi-Language Formatting Pipeline

| Feature | MegaLinter | pre-commit | harness-cc (ours) | Notes |
|---------|------------|------------|-------------------|-------|
| Language coverage | 69+ languages | Unlimited (community hooks) | 6 languages | harness-cc covers the languages harness-cc supports; coverage matches our scope |
| Parallel execution | Yes (multiprocessing) | Partial (per-hook) | No (sequential per-file) | Gap: `format-all.py` runs formatters sequentially. Parallel execution would improve write-latency for mixed-language projects |
| Auto-fix on edit | GitHub Action only | pre-commit hook | Yes (PostToolUse hook) | Advantage: harness-cc auto-formats during editing, not just at commit time |
| Encoding bridge | No | No | **Yes (GBK↔UTF-8)** | **Unique differentiator** — no competitor handles non-UTF-8 encodings transparently |
| CI mode | Primary use case | Optional | Not exposed | Gap: formatting `--check` mode not available as standalone command |
| Incremental (staged only) | No (full repo) | Yes (pre-commit) | Yes (single file via PostToolUse) | Aligned with best practice |
| Preset configurations | Yes (flavors) | No | No | Gap: harness-cc could offer formatting presets per project type (Qt Widgets vs Qt Quick vs pure C++) |

### State Machine / Progress Tracking

| Feature | task-orchestrator-py | Monoco Toolkit | harness-cc (ours) | Notes |
|---------|----------------------|----------------|-------------------|-------|
| State transitions | queue→work→review→done | Proposed→Approved→Doing→Review→Done | pending→in_progress→passed/failed | harness-cc has retry loop (failed→in_progress); others are linear |
| Dependency tracking | Yes (graph) | No | Yes (depends_on) | Aligned with best practice |
| Oracle verification | No | No | **Yes (build + test)** | **Unique differentiator** — requires evidence for state transition |
| Git integration | No | Yes (Issue as Code) | **Yes (auto-commit)** | harness-cc auto-commits on each `passed` transition |
| Session resilience | MCP persistent | Issue as Code | **Claude Code hooks** | harness-cc integrates with AI session lifecycle (PreCompact + Stop hooks) |
| Visual UI | No | VS Code Kanban | No (JSON only) | By design — CLI skill, no GUI |
| Parallel task support | No | No | Yes (parallel_group field) | Schema supports it, but not yet wired in scripts |

### Claude Code Skill Ecosystem

| Feature | claude-skills (community) | Superpowers plugin | harness-cc (ours) | Notes |
|---------|--------------------------|-------------------|-------------------|-------|
| SKILL.md entry | Yes | Yes | Yes | Standard requirement |
| Slash commands | Yes | Yes | 3 commands | Adequate for scope (setup / plan / review) |
| Multi-language agent support | No (single lang) | No (generic) | **6 languages, 23 agents** | **Unique in ecosystem** — most skills are single-language |
| State machine workflow | No | No | Yes | Only harness-cc has state machine progress tracking |
| Encoding bridge | No | No | **Yes (GBK↔UTF-8)** | **Unique in ecosystem** |
| MCP integration | Yes | Yes | Yes (4 servers) | Aligned with best practice |
| Hook integration (4 events) | Some have hooks | Some have hooks | **Yes (4 events, dual platform)** | Comprehensive hook coverage |
| Plugin marketplace | Yes (338 skills) | Yes | No | Gap: not yet packaged for marketplace distribution |

### Cross-Platform Hook System

| Feature | Lefthook | pre-commit | Husky | harness-cc (ours) | Notes |
|---------|----------|------------|-------|-------------------|-------|
| Cross-platform | Yes | Yes | Yes | Yes (bash+PowerShell) | All major tools support this |
| Parallel hook execution | **Yes (90% speedup)** | Partial | No | No | Gap: harness-cc hooks run sequentially; async PostToolUse would help |
| Hook events | git hooks | git hooks | git hooks | **Claude Code hooks (4 types)** | Different domain — Claude Code vs git hooks are complementary |
| Encoding bridge | No | No | No | **Yes** | **Unique** — no git-hook tool handles encoding |
| Non-blocking on failure | No (fails) | No (fails) | No (fails) | **Yes (exit 0)** | Intentional design: failure should not block AI session |
| Plugin ecosystem | No | Yes (3000+) | Yes (npm) | Marketplace (planned) | pre-commit's plugin ecosystem is the gold standard |
| Monorepo support | Excellent | Good | Excellent | N/A (per-project) | harness-cc is per-project by design |

---

## Sources

- [MegaLinter documentation](https://megalinter.io/) — multi-language formatting pipeline architecture, parallel execution, CI integration, flavors
- [linthis](https://pypi.org/project/linthis/) — parallel linting + formatting + security scanning with caching
- [OpenLens](https://www.npmjs.com/package/openlens) — AI code review with parallel agent architecture
- [Minion Engine](https://docs.rs/crate/minion-engine) — AI workflow orchestration for Claude Code with YAML-defined review workflows
- [Claude Code Skills Marketplace Guide](https://skywork.ai/blog/ai-bot/claude-code-skills-marketplace-ultimate-guide/) — ecosystem overview, features, best practices (2026)
- [claude-code-extensions](https://github.com/nodnarbnitram/claude-code-extensions) — 18 skills, 21 plugins, 60+ agents reference implementation
- [claude-skills by alirezarezvani](https://github.com/alirezarezvani/claude-skills) — 338 skills, largest collection reference
- [Claude Code Hooks Official Documentation](https://claude.com/blog/how-to-configure-hooks) — hook points, config patterns, best practices (Dec 2025)
- [anipotts/claude-code-tips](https://github.com/anipotts/claude-code-tips) — production hooks patterns, self-verification loop, statusline patterns (Apr 2026)
- [Claude Code Power User Patterns Issue #32407](https://github.com/anthropics/claude-code/issues/32407) — compaction quality, permission model patterns
- [Lefthook](https://github.com/evilmartians/lefthook) — parallel cross-platform git hooks, monorepo support
- [pre-commit](https://pre-commit.com/) — multi-language git hooks framework, plugin ecosystem
- [task-orchestrator-py](https://pypi.org/project/task-orchestrator-py/) — MCP server for AI agent state machine task tracking
- [Monoco Toolkit](https://pypi.org/project/monoco-toolkit/) — Issue as Code state machine for agentic engineering
- [LoopForge](https://pypi.org/project/loopforge/) — auditable state machine for CI/CD lifecycle
- [OpenHorizon Workflows](https://www.npmjs.com/package/@openhorizon/workflows) — MCP-based multi-agent workflow orchestration
- [ANTHROPIC CLAUDE.MD](https://claude.com/blog/how-to-configure-hooks) — official hook point reference and configuration schema
- [comparative analysis from morphllm.com](https://www.morphllm.com/claude-code-skills-mcp-plugins) — Skills vs MCP vs Plugins decision framework (2026)

---

## Research Quality Notes

- **Domain 1 (Formatting Pipeline):** High confidence — convergent findings across MegaLinter, pre-commit, Lefthook, and linthis all confirm the same patterns (auto-format, incremental, parallel, graceful failure).
- **Domain 2 (State Machine):** High confidence — task-orchestrator-py, Monoco, LoopForge, and OpenHorizon all implement similar state machines with dependency tracking. The harness-cc approach (pending→in_progress→passed/failed with retry) is aligned with best practices.
- **Domain 3 (Claude Code Skills):** High confidence — the ecosystem is well-documented with multiple large reference repositories. The skill plugin pattern (SKILL.md + agents + rules + hooks + MCP) is the definitive community standard.
- **Domain 4 (Cross-Platform Hooks):** High confidence — Claude Code hook documentation is thorough. Lefthook and pre-commit provide complementary patterns for cross-platform execution.
- **Encoding bridge uniqueness:** Lower confidence — while no competitor skill or tool in the searched results handles GBK↔UTF-8 transparently, there may be niche tools not captured in English-language search. Treat the "unique" claim as confirmed for the English-speaking ecosystem.

---

*Feature research for: ty-qt-ai-plugin (harness-cc) — Technical Debt Remediation Milestone*
*Researched: 2026-06-14*
