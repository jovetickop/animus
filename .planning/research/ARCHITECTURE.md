# Architecture Research

**Domain:** Claude Code skill plugin / multi-language code review orchestration framework
**Researched:** 2026-06-14
**Confidence:** HIGH

## Current Architecture Assessment

The harness-cc plugin uses a **three-layer microkernel** architecture (Skill Entry -> Orchestration -> Execution) with 7 subsystems. The existing architecture is well-conceived for its original design goals, but codebase analysis (`CONCERNS.md`) reveals structural debt from organic growth:

| Subsystem | Current State | Issues |
|-----------|--------------|--------|
| State machine engine | `update-progress.ps1` monolithic (424 lines) | Single-responsibility violated; validation, oracle, reporting, git commit all in one file |
| Hook scripts | 12 files in `hooks/scripts/` (`.ps1` + `.sh` + `.py`) | Path-finding logic duplicated 6+ times across files; encoding conversion scattered |
| Path resolution | Ad-hoc per script | 5+ different approaches: `$PSScriptRoot/../../..`, `cd`-based traversal, relative from CWD |
| Encoding bridge | `encoding-bridge.py` + inline in `pre-tool-use.ps1/.sh` | Works correctly but boundaries unclear; which scripts should call it vs. which should not is undocumented |
| Plugin manifest | No `plugin.json`; uses `SKILL.md` as entry | Pre-dates official Claude Code plugin spec; misses standardized discovery |
| Scripts directory | Split between `scripts/` (repo-level) and `.claude/scripts/` | Dual locations with unclear ownership |

**Good:** The layered Agent inheritance (`base/ -> universal/ -> {lang}/`), template deployment (`templates/` -> target project), and dual-platform hooks (`bash || powershell || exit 0`) are solid patterns that match industry practice.

**Needs work:** Script organization, path management, encoding boundaries, and conformance to the official Claude Code plugin spec.

---

## Recommended Architecture Improvements (Based on Research)

### 1. Adopt Official Plugin Spec Layout

The current layout predates the official Claude Code plugin spec. The spec prescribes:

```
plugin-root/
├── .claude-plugin/
│   └── plugin.json          # Required: Plugin manifest (MISSING)
├── commands/                  # Slash commands (PRESENT)
├── agents/                    # Subagent definitions (PRESENT)
├── skills/                    # Agent skills (PRESENT)
├── hooks/                     # Event handlers (PRESENT)
│   └── hooks.json
├── .mcp.json                  # MCP servers (PRESENT)
└── scripts/                   # Shared utilities (PRESENT, but split)
```

**Gap:** harness-cc is missing `.claude-plugin/plugin.json`. The `SKILL.md` entry point is the legacy (pre-plugin-spec) approach. Adding a manifest enables:
- Official marketplace compatibility
- `userConfig` prompts for install-time configuration
- Proper version tracking
- `CLAUDE_PLUGIN_DATA` for persistent caches (node_modules, etc.)

**Migration is low-risk** because the spec is additive: `plugin.json` coexists with `SKILL.md`; `SKILL.md` continues to work as the `/harness-cc` entry.

### 2. Consolidate Path Resolution into a Single Module

The single biggest source of duplication is path-finding logic. Research of community patterns (PowerShell module design, TAKT, HVE Core) converges on the **Path Provider Singleton** pattern:

**Before:** Each script independently computes its way to `.claude/state/features.json` using different techniques (regex, `$PSScriptRoot` arithmetic, `cd` traversal). 6+ variants exist.

**After:** One centralized module resolves all paths. Scripts call into it instead of computing their own.

```
# One source of truth (Python, for cross-platform reach):
scripts/
├── path_resolver.py          # Centralized path resolution
├── shared/                   # Reusable utility package
│   ├── __init__.py
│   ├── resolver.py           # ResolvePluginRoot, FindProjectRoot, LocateStateFile
│   ├── encoding.py           # Encoding detection and conversion
│   └── logging.py            # Unified logging
```

This mirrors the `Core/Platform.psm1` pattern from the PowerShell module community (danielshue/notebook-automation, joelvaneenwyk/hyper-v-automation).

### 3. Decompose `update-progress.ps1` into Domain Modules

The 424-line monolith mixes 6 responsibilities. The PowerShell module community consensus (PowershellPracticeAndStyle, mikefrobbins.com) prescribes **one function per file, one domain per module**:

| Current Code Block | Extracted Module | Responsibility |
|---|---|---|
| Lines 1-60: Parameter/argument validation | `validate-transition.ps1` | State transition legality check (5-state matrix, DAG dependency check) |
| Lines 61-120: Path/resource resolution | `path-resolver.ps1` | Locate features.json, project-config.json, state directory |
| Lines 121-200: Transition execution + Oracle verification | `oracle-runner.ps1` | Execute build/test commands, capture exit codes |
| Lines 201-280: Report generation | `report-generator.ps1` | Generate `docs/reports/<TaskId>-<name>.md` |
| Lines 281-350: Progress log update | `progress-logger.ps1` | Append to `claude-progress.txt` |
| Lines 351-424: Git commit | `git-committer.ps1` | Auto-commit with Conventional Commit message |

The `update-progress.ps1` wrapper becomes a thin orchestrator ( ~30 lines) that imports and calls the domain modules in sequence. This pattern reduced a 2,326-line monolith to ~200 lines (87% reduction) in a documented PowerShell refactoring case study (naz-hage/ntools).

### 4. Normalize the Scripts Directory Hierarchy

Currently scripts are scattered:
- `.claude/hooks/scripts/` — hook-specific scripts
- `.claude/scripts/` — session-catchup.py (why here vs. hooks?)
- `scripts/` — repo-level Python ports of PS scripts

The official plugin spec prescribes root-level `scripts/` for shared utilities, while `hooks/scripts/` remains for hook-specific code. The boundary rule:

| Location | Contains | Referenced By |
|----------|----------|---------------|
| `scripts/shared/` | Cross-cutting utilities (path resolution, encoding bridge, logging) | Hooks, commands, and other scripts import from here |
| `scripts/formatters/` | Language-specific formatter invocations | `format-all.py` dispatches to sub-scripts here |
| `hooks/scripts/` | Hook-specific glue scripts only (pre-tool-use.ps1, pre-compact.ps1, stop-check.ps1, clang-format.ps1) | `hooks.json` |
| `.claude/scripts/` | Remove; merge into `scripts/` | N/A — eliminated |

**Rationale:** The `hooks/scripts/` boundary is "thin glue that configures and fires the shared utilities." If a script contains path-finding or encoding logic, it belongs in `scripts/shared/`.

---

## Component Boundaries

### Boundary 1: Path Resolution (must be extracted first)

**What:** All logic that locates project root, `.claude/` directory, state files, config files.
**Current duplication:** 6+ implementations across hook scripts and state engine.
**Recommended boundary:** Single `scripts/shared/resolver.py` + `scripts/shared/path-resolver.ps1` (dual-platform). All scripts import from these; never inline path logic.
**Dependency:** None (extract first — everything else needs paths).

### Boundary 2: Encoding Bridge

**What:** GBK <-> UTF-8 detection and conversion for file content.
**Current state:** `encoding-bridge.py` exists but its callers are inconsistent — `pre-tool-use.ps1` calls it, but some scripts do their own conversion.
**Recommended boundary:** The encoding bridge is internal to the hooks system. Only `pre-tool-use.ps1` (PreToolUse) and a new `post-tool-use.ps1` (PostToolUse, wrapping existing encoding bridge call) should touch encoding. All other scripts read/write UTF-8 only.
**Dependency:** Depends on path resolution (needs to know file locations).

### Boundary 3: State Machine Core

**What:** State transition validation logic (`pending -> in_progress -> passed/failed`).
**Current state:** Embedded in `update-progress.ps1` alongside oracle, reporting, and git logic.
**Recommended boundary:** `templates/harness/state-machine/validate-transition.ps1` — pure validation, no side effects. Returns `$true/$false` + error message.
**Dependency:** Depends on path resolution (to read `features.json`), but not on encoding bridge or git.

### Boundary 4: Oracle Runner

**What:** Executing the configured build/test commands and capturing results.
**Current state:** Mixed into `update-progress.ps1`; uses `Invoke-Expression` (security risk).
**Recommended boundary:** `templates/harness/state-machine/oracle-runner.ps1` — uses `Start-Process` with argument arrays instead of `Invoke-Expression`.
**Dependency:** Depends on path resolution (to locate `project-config.json` and `features.json`).

### Boundary 5: Report Generator

**What:** Generating Markdown reports from task state.
**Current state:** Inline in `update-progress.ps1`.
**Recommended boundary:** `templates/harness/state-machine/report-generator.ps1` — pure formatting, no side effects.
**Dependency:** Depends on path resolution (to know where to write reports).

### Boundary 6: Git Integration

**What:** Auto-commit after task completion, commit message formatting.
**Current state:** Inline in `update-progress.ps1`.
**Recommended boundary:** `scripts/shared/git-helper.ps1` — also usable by hooks (e.g., pre-compact could check dirty state).
**Dependency:** Independent; only depends on `git` being on PATH.

---

## Data Flow

### Encoding Conversion Flow

```
File Write/Edit Event
    │
    ▼
PreToolUse Hook
    │
    ├── 1. Read file content as raw bytes
    ├── 2. Detect encoding (BOM-based, heuristic fallback)
    ├── 3. If GBK detected → convert to UTF-8 via encoding-bridge.py
    └── 4. Write back as UTF-8
    │
    ▼
Claude Code processes file (UTF-8)
    │
    ▼
PostToolUse Hook
    │
    ├── 1. If project-config.json `encoding` == "gbk"
    │   ├── a. Read file content
    │   ├── b. Convert UTF-8 → GBK via encoding-bridge.py
    │   └── c. Write back as GBK
    └── 2. Run formatters (clang-format, cargo fmt, etc.)
```

**Critical rule:** The encoding bridge is a **boundary service** — only the two hooks touch it. State machine scripts (`update-progress.ps1`, etc.) read/write UTF-8 only. This eliminates the possibility of encoding mismatch mid-pipeline.

### State Transition Flow

```
User or Agent requests transition: <TaskId> <newStatus>
    │
    ▼
update-progress.ps1 (thin orchestrator)
    │
    ├── 1. path-resolver.ps1 → locate features.json
    ├── 2. validate-transition.ps1 → check legality (5-state matrix)
    │       ├── If illegal → exit 1 with error message
    │       └── If legal → continue
    ├── 3. oracle-runner.ps1 (only if target is "passed")
    │       ├── Execute verify_command from features.json
    │       ├── If fails → set status="failed", capture error output
    │       └── If passes → continue to mark passed
    ├── 4. Update features.json (status, updated_at, last_error)
    ├── 5. report-generator.ps1 → write docs/reports/<TaskId>.md
    ├── 6. progress-logger.ps1 → append to claude-progress.txt
    └── 7. git-helper.ps1 (only if passed) → git commit
```

### Hook Execution Flow (Revised)

```
hooks.json triggers event
    │
    ▼
Hook script (.sh primary, .ps1 fallback)
    │
    ├── 1. Call scripts/shared/resolver.py to locate project root
    │   (NO inline path logic — delegate to shared module)
    ├── 2. Perform hook-specific work
    │   (pre-tool-use: backup + encoding)
    │   (post-tool-use: formatting + encoding)
    │   (pre-compact: flush progress)
    │   (stop: check incomplete tasks)
    └── 3. exit 0 (never block the workflow)
```

---

## Build Order / Refactoring Dependencies

The refactoring has strict dependency ordering. Installing the wrong phase first breaks everything.

```
Phase 1: Encoding Normalization (TECHD-01, 02, 03)
    ├── Prerequisite for all other phases
    ├── UTF-16LE → UTF-8 with BOM for all .ps1 files
    ├── CRLF → LF for all .sh files
    └── Repair corrupted Chinese comments in UTF-16LE files
    │
    ▼
Phase 2: Path Management Extraction (TECHD-04, 05)
    ├── Depends on Phase 1 (need clean encoding to refactor scripts)
    ├── Create scripts/shared/resolver.py + path-resolver.ps1
    ├── Standardize on .claude/state/ as single state path
    └── Remove dual-path fallback logic from all scripts
    │
    ▼
Phase 3: Script Module Split (TECHD-06)
    ├── Depends on Phase 2 (need shared path module first)
    ├── Extract validate-transition.ps1 from update-progress.ps1
    ├── Extract oracle-runner.ps1 from update-progress.ps1
    ├── Extract report-generator.ps1 from update-progress.ps1
    ├── Extract progress-logger.ps1 from update-progress.ps1
    └── Extract git-helper.ps1 from update-progress.ps1
    │
    ▼
Phase 4: Security Hardening (TECHD-07, 08)
    ├── Depends on Phase 2-3 (scripts need to exist before fixing them)
    ├── Replace Invoke-Expression with Start-Process + argument arrays
    ├── Replace regex JSON parsing with ConvertFrom-Json
    └── Add error logging (not silent /dev/null)
    │
    ▼
Phase 5: Remaining Fixes (TECHD-09, 10, 11)
    ├── format-all.py Rust cargo fmt deduplication
    ├── init-project.ps1 hardcoded path repair
    └── Documentation for encoding strategy, template roles, hook debugging
```

**Do not attempt Phase 3 before Phase 2.** Splitting scripts while path logic is scattered creates 7 places to update instead of 1. The path module is the keystone.

---

## Patterns to Adopt

### Pattern 1: Domain-Organized Script Module

**What:** Group scripts by domain responsibility, not by file type or chronology. Each module has a `Public/` (exported functions) and `Private/` (internal helpers) boundary.

**Source:** PowerShell community standards (PowershellPracticeAndStyle, mikefrobbins.com), TAKT agent coordination topology.

**When to use:** Any script that exceeds 100 lines or has more than one responsibility.

**Trade-offs:**
- Pro: Single source of truth; change one place, all consumers update
- Pro: Testable in isolation (Pester tests per module)
- Con: Slightly more complex to load (dot-sourcing orchestration)
- Con: Overkill for trivial helper scripts under 30 lines

**Recommended structure for harness-cc:**
```
templates/harness/
├── update-progress.ps1           # Thin orchestrator (~30 lines)
├── modules/
│   ├── Public/
│   │   ├── validate-transition.ps1
│   │   ├── oracle-runner.ps1
│   │   ├── report-generator.ps1
│   │   ├── progress-logger.ps1
│   │   └── git-helper.ps1
│   └── Private/
│       ├── features-json-io.ps1   # Read/write JSON file (internal)
│       └── state-string-format.ps1 # Format status strings (internal)
```

### Pattern 2: Path Provider Singleton

**What:** A single module that exports functions to resolve all canonical path locations. Every other script calls into it; no script computes its own paths.

**Source:** `Core/Platform.psm1` pattern from PowerShell module community, `CLAUDE_PLUGIN_ROOT` convention from official Claude Code plugin spec.

**When to use:** Any project with 3+ scripts that need to locate files relative to project root.

**Trade-offs:**
- Pro: Eliminates the #1 source of bugs (path inconsistency)
- Pro: Adding a new path only changes one file
- Con: Adds a dependency that must be loaded before any other script runs

**Example interface:**
```python
# scripts/shared/resolver.py
def find_project_root(start_path: str = None) -> str:
    """Walk up from start_path looking for .claude/harness/project-config.json"""
    
def locate_state_file(state_dir: str = None) -> str:
    """Return the canonical features.json path"""
    
def locate_config_file() -> str:
    """Return the canonical project-config.json path"""
    
def locate_reports_dir() -> str:
    """Return docs/reports/ path, create if missing"""
```

### Pattern 3: Encoding Bridge Boundary

**What:** Encoding conversion is a **sandwich** — the PreToolUse hook converts GBK -> UTF-8 before AI processing; the PostToolUse hook converts UTF-8 -> GBK after. No other component touches encoding.

**Source:** This pattern is unique to harness-cc's GBK support requirement; no general-purpose equivalent found in the broader ecosystem.

**When to use:** Projects that must preserve legacy file encodings (GBK, Shift-JIS, etc.) while using modern UTF-8 tools internally.

**Trade-offs:**
- Pro: Simple mental model — "hooks handle encoding, everything else is UTF-8"
- Pro: If encoding corruption occurs, the bug is in exactly one of two places
- Con: Adds latency to every Write/Edit (file must be read, converted, written)
- Con: Requires `project-config.json` to explicitly declare encoding (default: none/UTF-8)

**Critical implementation detail:** The encoding bridge must use **file-format heuristics, not just BOM detection** — some GBK files lack BOM. The current `encoding-bridge.py` should be enhanced to detect GBK by byte pattern (range 0x81-0xFE for lead bytes) when BOM is absent.

### Pattern 4: Declarative Workflow Definition (TAKT style — Future)

**What:** Define review pipelines as declarative YAML/JSON rather than embedding workflow logic in scripts. Each phase (plan, implement, review, fix) gets its own persona, permissions, and output contract.

**Source:** TAKT Agent Koordination Topology, GodModeSkill lineage quorum, HVE Core skill stacking.

**When to use:** When the project needs to support multiple workflow variants (TDD, code-review-only, bug-fix-only) without rewriting scripts.

**Current status in harness-cc:** The `features.json` dependency DAG plus `depends_on` and `parallel_group` fields already approximates this. Official adoption would mean extracting workflow definitions from `SKILL.md` into a structured config file.

**Trade-offs:**
- Pro: Workflow changes don't require script changes
- Pro: Multiple workflow profiles possible (strict TDD, fast review, hotfix)
- Con: YAML complexity — easier to debug a script than a DAG definition
- Con: Overkill for single-workflow projects

**Recommendation:** Defer this pattern to a later milestone. The immediate priority is fixing the existing architecture before adding workflow abstraction.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Copy-Paste Path Resolution

**What people do:** Each new script independently computes "where is my project root" by walking up `$PSScriptRoot`. The 7th script gets it subtly wrong (one too many `..`).

**Why it's wrong:** bugs compound silently; fixing a path requires editing all scripts; `git grep` for path logic returns 15 hits and you can't tell which are correct.

**Do this instead:** Extract once. `Import-Module scripts/shared/path-resolver.ps1` or `from resolver import find_project_root`. Every script uses that.

### Anti-Pattern 2: Mixed Encoding Mid-Pipeline

**What people do:** Some scripts write UTF-8, some write GBK, some auto-detect. A file written by script A is unreadable by script B.

**Why it's wrong:** Encoding corruption is silent — the bytes are wrong but the file still "exists." Detection only happens at runtime when a tool chokes on the encoding.

**Do this instead:** All scripts write UTF-8. Only the PreToolUse/PostToolUse hooks touch encoding conversion. Document this as a hard rule.

### Anti-Pattern 3: Silent Hook Failures

**What people do:** Hooks swallow all errors with `2>/dev/null || exit 0` because "they must not block the workflow."

**Why it's wrong:** When encoding conversion silently fails (dependency missing, path wrong, encoding mismatch), files are silently corrupted. The user only notices hours later.

**Do this instead:** Log errors to `CLAUDE_PLUGIN_DATA` (survives plugin updates) or a dedicated `.claude/hooks/hook-errors.log`. Still `exit 0` (don't block), but make failures discoverable. Add `|| tee -a "${CLAUDE_PLUGIN_DATA}/hook-errors.log"` pattern.

### Anti-Pattern 4: Dual-Maintenance Shell + PowerShell

**What people do:** Maintain identical logic in `.sh` and `.ps1` files, drifting over time as fixes land in one but not the other.

**Why it's wrong:** The hooks.json fallback chain `bash X.sh || powershell X.ps1` makes it hard to know which branch is actually executing, and even harder to test both.

**Do this instead:** Write cross-platform logic in **Python** (Python 2/3 compatible, per existing constraint). The `.sh` and `.ps1` become thin wrappers that call the Python script. If Python is unavailable, the `.sh` or `.ps1` falls back to inline logic (bare minimum — path resolution only).

### Anti-Pattern 5: Speculative Feature Extraction

**What people do:** Extract modules for functionality that isn't yet duplicated ("we might need this later").

**Why it's wrong:** Premature modularity adds indirection without payoff. Three readers of the code must now understand an import chain that only touches one file.

**Do this instead:** Wait for duplication. A function used in 1 place stays inline. A function used in 2+ places gets extracted. The path resolver and encoding bridge are exceptions (they are already duplicated 6x and 3x respectively).

---

## Integration With Claude Code Plugin Spec

### Current Gap Analysis

| Spec Element | Status in harness-cc | Action Required |
|---|---|---|
| `.claude-plugin/plugin.json` | Missing — SKILL.md as entry point | Create minimal `plugin.json` (name, version, description) |
| `commands/` at root level | Present (within `.claude/commands/`) | Relocate to root `commands/`? Breaking change for installed projects. Weigh against backward compat. |
| `agents/` at root level | Present (within `.claude/agents/`) | Same relocation question |
| `${CLAUDE_PLUGIN_ROOT}` usage | Absent — hardcoded paths | Replace with `${CLAUDE_PLUGIN_ROOT}` in hooks.json, commands, scripts |
| `${CLAUDE_PLUGIN_DATA}` for caches | Not used | Use for `Cargo.toml` cache, formatter tool checks |
| `userConfig` for install-time config | Manual via init-project.ps1 | Migrate encoding preference, project type to `userConfig` |
| `monitors/` for background tasks | Not used | Optional for future (watch task completion) |

### Key Decision: .claude/ Relocation

The official spec places commands, agents, skills at **plugin root** (not inside `.claude/`). harness-cc puts them inside `.claude/`. This is a structural difference but not a functional blocker:

- The spec says "component directories MUST be at plugin root"
- But the spec also supports custom paths via `plugin.json`: `"agents": [".claude/agents"]`
- **Recommendation:** Add `plugin.json` with custom paths pointing to the existing `.claude/` structure. No file relocation needed. This preserves backward compatibility with installed projects while satisfying the manifest requirement.

**plugin.json (proposed):**
```json
{
  "name": "harness-cc",
  "version": "3.0.0",
  "description": "Multi-language coding workflow engine for Claude Code",
  "commands": "./.claude/commands",
  "agents": ["./.claude/agents"],
  "skills": "./.claude/skills",
  "hooks": "./.claude/hooks/hooks.json",
  "userConfig": {
    "default_encoding": {
      "type": "string",
      "description": "Default file encoding for target project (utf-8 or gbk)",
      "default": "utf-8"
    }
  }
}
```

---

## Source Code Organization (Refactored)

### Repository Root

```
ty-qt-ai-plugin/
├── .claude-plugin/
│   └── plugin.json              # NEW — Plugin manifest
├── SKILL.md                     # Existing — preserved for backward compat
├── .claude/
│   ├── agents/                  # Unchanged — 23 agent definitions
│   ├── commands/                # Unchanged — 3 slash commands
│   ├── rules/                   # Unchanged — 12 rule files
│   ├── hooks/                   # Unchanged structure, scripts slimmed
│   │   ├── hooks.json
│   │   └── scripts/
│   │       ├── pre-tool-use.ps1      # SLIMMED — delegates to shared/
│   │       ├── pre-compact.ps1       # SLIMMED — delegates to shared/
│   │       ├── stop-check.ps1        # SLIMMED — delegates to shared/
│   │       └── clang-format.ps1      # SLIMMED — delegates to shared/
│   ├── templates/               # Unchanged structure, modules added
│   │   ├── harness/
│   │   │   ├── update-progress.ps1   # SLIMMED — thin orchestrator
│   │   │   ├── modules/              # NEW — domain modules
│   │   │   │   ├── Public/
│   │   │   │   └── Private/
│   │   │   ├── show-status.py
│   │   │   └── run-regression.ps1
│   │   ├── state/
│   │   └── existing_project/
│   ├── skills/
│   └── scripts/                 # REMOVED — merged into scripts/shared/
├── scripts/                     # REORGANIZED — shared utilities
│   ├── shared/
│   │   ├── resolver.py          # NEW — path resolution (Python)
│   │   ├── encoding_bridge.py   # EXTRACTED from hooks
│   │   ├── logging.py           # NEW — unified logging
│   │   └── git_helper.py        # NEW — git operations
│   ├── formatters/
│   │   ├── format_all.py        # Keep, slim
│   │   └── rust_cache.py        # NEW — Cargo.toml cache for formatting
│   ├── hooks/                   # NEW — shared hook utilities
│   │   └── path-fns.sh          # Shared path functions for shell hooks
│   └── update-progress.py       # Existing — Python port
```

### Target Project `.claude/harness/` (after install)

```
.claude/harness/
├── update-progress.ps1          # Orchestrator (thin)
├── modules/                     # NEW — installed alongside scripts
│   ├── Public/
│   │   ├── validate-transition.ps1
│   │   ├── oracle-runner.ps1
│   │   ├── report-generator.ps1
│   │   ├── progress-logger.ps1
│   │   └── git-helper.ps1
│   └── Private/
│       ├── features-json-io.ps1
│       └── state-string-format.ps1
├── show-status.py
├── run-regression.ps1
├── init.ps1
├── coding-session.ps1
├── project-config.json
└── features.json
```

---

## Scaling Considerations

This project is a **developer tool**, not a consumer-facing service. The "scale" question is about codebase size and language coverage, not user count.

| Codebase State | Architecture Suitability | Pain Points |
|----------------|-------------------------|-------------|
| 1-5 languages, <50 script files | Current architecture is fine | Minimal — just fix encoding |
| 6-10 languages, 50-150 script files | Needs modularization (this proposal) | Path duplication, monolith scripts |
| 10+ languages, 150+ script files | Needs YAML workflow abstraction (TAKT style) | Workflow logic embedded in SKILL.md; hard to add new workflow types |

**Current state:** 6 languages, ~50 script files across templates, hooks, and tools. The modularization proposed here is appropriate for this scale. The YAML workflow abstraction (Pattern 4) should be deferred until language coverage exceeds 10 or workflow variants exceed 3.

---

## Sources

- **Claude Code Plugins Reference (official):** https://code.claude.com/docs/en/plugins-reference — Plugin manifest, component discovery, `${CLAUDE_PLUGIN_ROOT}` convention
- **Claude Code Plugin Structure Skill (official):** https://github.com/anthropics/claude-plugins-official — Directory layout specification
- **TAKT Agent Koordination Topology:** https://github.com/nrslib/takt — Declarative YAML workflow state machines for agent orchestration
- **GodModeSkill / Chorus:** https://github.com/99xAgency/GodModeSkill — Multi-LLM cross-review with lineage quorum voting
- **HVE Core Language Skills (Microsoft):** https://microsoft.github.io/hve-core/docs/agents/code-review/language-skills/ — Pluggable skill-based review standards with auto-discovery
- **Codeband:** https://github.com/thenvoi/codeband — Adversarial multi-model coding agents with git worktree isolation
- **PowerShell Script Module Design Philosophy (mikefrobbins.com):** https://mikefrobbins.com/2018/09/21/powershell-script-module-design-philosophy/ — Dev/production dual strategy, one function per file
- **PowerShellPracticeAndStyle — Building Reusable Tools:** https://github.com/richy58729/PowerShellPracticeAndStyle/blob/master/Best-Practices/Building-Reusable-Tools.md — Tool vs. controller distinction, parameter design
- **Creating a Scalable PowerShell Environment (MS DevBlogs):** https://devblogs.microsoft.com/powershell-community/creating-a-scalable-customised-running-environment/ — Auto-loading module patterns
- **harness-cc Existing Architecture (codebase analysis):** `.planning/codebase/ARCHITECTURE.md` — Current three-layer architecture
- **harness-cc Existing Concerns:** `.planning/codebase/CONCERNS.md` — Identified technical debt (encoding, path duplication, monolith scripts)

---
*Architecture research for: harness-cc Claude Code skill plugin*
*Researched: 2026-06-14*
