# Phase 2: Security & Robustness - Research

**Researched:** 2026-06-15
**Domain:** Security hardening and robustness improvements for harness-cc
**Confidence:** HIGH

## Summary

Phase 2 addresses three technical debt items: TECHD-07 (Invoke-Expression replacement), TECHD-08 (JSON regex parsing replacement), and TECHD-09 (Rust formatting dedup and caching). All three have well-established solution patterns from Microsoft and community consensus. This phase depends on Phase 1 completing first (UTF-8 encoding required before modifying script content).

Key findings:
- **TECHD-07**: `run-regression.ps1` has 3 `Invoke-Expression` calls (lines 16, 24, 40) that should be replaced with `&` calling operator — safest PS 5.1-compatible approach
- **TECHD-08**: 4 hook scripts use fragile regex/sed to parse JSON from stdin — replace with `ConvertFrom-Json` (PowerShell) and `jq` or Python (Shell)
- **TECHD-09**: `format-all.py` executes `cargo fmt --check` then `cargo fmt` redundantly, and doesn't cache `Cargo.toml` directory lookup

**Primary recommendation:** TECHD-07 and TECHD-08 are independent fixes that can be planned in parallel. TECHD-09 is a Python-only change. All three should be committed separately for easy rollback.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TECHD-07 | Replace `Invoke-Expression` in `run-regression.ps1` with safe alternatives | Microsoft official guidance on `Invoke-Expression` risks, PSScriptAnalyzer `AvoidUsingInvokeExpression` rule |
| TECHD-08 | Replace regex JSON parsing in hook scripts with `ConvertFrom-Json` | PowerShell 5.1 native JSON parser, Claude Code hooks stdin format documented |
| TECHD-09 | Fix `format-all.py` Rust double `cargo fmt` and cache `Cargo.toml` lookup | Python stdlib caching patterns, `format-all.py` lines 68-84 confirmed |

## Research Questions

### Q1: TECHD-07 — Invoke-Expression Replacement

**Problem:** `run-regression.ps1` uses `Invoke-Expression` in 3 places to execute commands from JSON config:
- Line 16: `Invoke-Expression $buildCmd`
- Line 24: `Invoke-Expression $testCmd`
- Line 40: `Invoke-Expression $testCmd`

**What commands look like:** From `project-config.json`, commands are strings like `python -m pytest tests/ -v` or `cargo test`.

**Best replacement pattern for PS 5.1:**

Option A — `&` calling operator (recommended):
```powershell
# Split command string into program + arguments
$parts = $buildCmd.Split(' ', 2)
$exe = $parts[0]
$args = if ($parts.Length -gt 1) { $parts[1] } else { "" }

# Use & operator - treats $exe as command name, $args as string argument
& $exe $args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Option B — `Start-Process` with `-ArgumentList` (more isolation):
```powershell
$parts = $buildCmd.Split(' ', 2)
Start-Process -FilePath $parts[0] -ArgumentList $parts[1] -Wait -NoNewWindow -PassThru | Select-Object -ExpandProperty ExitCode
```

**Recommendation:** Use `&` calling operator. It's:
- Safe: command name and arguments are separated — injection risk eliminated
- PS 5.1 compatible: works on all PowerShell versions
- Simple: minimal code change

**Edge cases to handle:**
1. Commands with no arguments (`cargo test` without args) — split produces `[cmd]` array of length 1
2. Commands with multiple arguments (`python -m pytest tests/ -v -s`) — Split with limit=2 keeps remaining args together
3. Empty/whitespace-only commands — already checked with `IsNullOrWhiteSpace` in existing code, preserve this check

**What to verify after fix:**
- `git grep 'Invoke-Expression' run-regression.ps1` returns empty
- PSScriptAnalyzer `AvoidUsingInvokeExpression` returns 0 warnings for the file
- Commands still execute correctly: `python -m pytest tests/ -v` still runs pytest

**[VERIFIED: Microsoft "Avoid using Invoke-Expression" + PSScriptAnalyzer rule documentation]**

---

### Q2: TECHD-08 — JSON Regex Parsing Replacement

**Problem:** 4 hook scripts use fragile regex or sed to extract JSON fields from stdin input.

**Affected files:**
| File | Lines | Current Pattern | Issue |
|------|-------|----------------|-------|
| `clang-format.ps1` | 3-6 | `$inputJson -notmatch '"file_path"\s*:\s*"([^"]+)"'` | Regex breaks on escaped quotes, special chars in paths |
| `pre-tool-use.ps1` | 5-20 | `$inputJson -match '"tool"\s*:\s*"([^"]+)"'` etc. | Same fragility + duplicate logic |
| `clang-format.sh` | 4-5 | `sed -n 's/.*"file_path":"\([^"]*\)".*/\1/p'` | sed doesn't handle JSON escaping |
| `pre-tool-use.sh` | 6-21 | `sed -n 's/.*"tool":"\([^"]*\)".*/\1/p'` etc. | Same fragility |

**Note:** `pre-compact.ps1` and `stop-check.ps1` already use `ConvertFrom-Json` correctly — no change needed.

**PowerShell fix pattern:**
```powershell
# Read stdin as object
$inputObj = $input | Out-String | ConvertFrom-Json

# Extract fields safely
$filePath = $inputObj.tool_input.file_path
$operation = $inputObj.tool  # or $inputObj.name

if (-not $filePath) { exit 0 }
```

**Edge cases for PowerShell:**
1. **Null `file_path`**: `$inputObj.tool_input.file_path` returns `$null`, `if (-not $filePath)` catches it
2. **Missing `tool_input` property**: `$inputObj.tool_input` returns `$null`, accessing `.file_path` on `$null` returns `$null` — still safe due to null check
3. **Nested JSON**: Claude Code hooks stdin format is always `{tool_name, tool_input{file_path, ...}}` — flat enough
4. **Special characters in paths**: `ConvertFrom-Json` handles Unicode correctly; paths like `C:\用户\文档\测试.cpp` work fine

**Shell fix pattern (bash/sh):**
Option A — `jq` (if available):
```bash
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
[ -z "$file_path" ] && exit 0
```

Option B — Python (since `format-all.py` already requires Python):
```bash
file_path=$(python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
```

**Current shell scripts use `sed` because `jq` availability is uncertain and Python adds startup overhead.** However, since these hooks already call `python` for `encoding-bridge.py` in `pre-tool-use.ps1`, the Python approach is consistent.

**Decision for Shell:**
- `clang-format.sh`: Keep minimal (no GBK/encoding bridge) — use `jq` if available, fallback to Python
- `pre-tool-use.sh`: Use Python (consistent with `pre-tool-use.ps1` which already calls Python)

**Critical requirement:** "Failure does not block" semantics must be preserved. If JSON parsing fails, `exit 0` (not `exit 1`).

**[VERIFIED: PowerShell 5.1 ConvertFrom-Json API + Claude Code hooks stdin format]**

---

### Q3: TECHD-09 — format-all.py Rust Dedup and Cache

**Problem:** `format-all.py` `format_rust()` function (lines 68-84):
1. Executes `cargo fmt --check` then `cargo fmt` — first call output is completely ignored
2. `Cargo.toml` directory lookup traverses from file path upward on every call (no caching)

**Current code:**
```python
def format_rust(file_path):
    current_dir = os.path.dirname(os.path.abspath(file_path))
    while current_dir:
        if os.path.exists(os.path.join(current_dir, "Cargo.toml")):
            try:
                proc = subprocess.Popen(
                    ["cargo", "fmt", "--check"],  # <-- useless, result ignored
                    cwd=current_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                proc.communicate(timeout=60)
                # cargo fmt 没有 --files 选项，对整个项目执行
                proc2 = subprocess.Popen(
                    ["cargo", "fmt"],  # <-- only this one matters
                    cwd=current_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                proc2.communicate(timeout=60)
                if proc2.returncode == 0:
                    print(u"[format-all] {0}: cargo fmt OK".format(file_path))
                    return
            except Exception:
                return
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
```

**Fix 1 — Remove redundant `--check`:**
Simply remove lines 68-75 (the `--check` call). Single `cargo fmt` call is sufficient.

**Fix 2 — Cache `Cargo.toml` directory lookup:**
```python
# Module-level cache: maps file_path_dir -> cargo_root_dir
_cargo_root_cache = {}

def _find_cargo_root(file_path):
    """Find and cache Cargo.toml directory for a given file path."""
    dir_path = os.path.dirname(os.path.abspath(file_path))
    if dir_path not in _cargo_root_cache:
        current = dir_path
        while current:
            if os.path.exists(os.path.join(current, 'Cargo.toml')):
                _cargo_root_cache[dir_path] = current
                break
            parent = os.path.dirname(current)
            if parent == current:
                _cargo_root_cache[dir_path] = None
                break
            current = parent
        else:
            _cargo_root_cache[dir_path] = None
    return _cargo_root_cache[dir_path]

def format_rust(file_path):
    """格式化 Rust 文件：在项目根目录执行 cargo fmt"""
    root = _find_cargo_root(file_path)
    if not root:
        return
    try:
        proc = subprocess.Popen(
            ["cargo", "fmt"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout_data, stderr_data = proc.communicate(timeout=60)
        if proc.returncode == 0:
            print(u"[format-all] {0}: cargo fmt OK".format(file_path))
    except Exception:
        pass
```

**Python 2/3 compatibility:** Uses only stdlib — `_cargo_root_cache` is a plain dict (works in Py2), `os.path.exists` works in both.

**Verification:**
- `git grep 'cargo fmt --check' format-all.py` should return empty after fix
- Cache hit rate can be verified by adding debug print (temporary)

**[VERIFIED: format-all.py lines 68-84 confirmed + Python stdlib dict caching pattern]**

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Command execution (run-regression.ps1) | API/Backend | — | Executes build/test commands from config — security-sensitive |
| JSON parsing in hooks | Hook Scripts | — | PreToolUse/PostToolUse hooks parse stdin — must be robust |
| Rust formatting | Hook Scripts | — | Part of PostToolUse formatting pipeline |
| Encoding conversion | Hook Scripts | — | Only PreToolUse/PostToolUse hooks touch encoding |

---

## Standard Stack

### PowerShell Security Patterns

| Library/Pattern | Version | Purpose | Why Standard |
|----------------|---------|---------|-------------|
| `&` calling operator | PS 5.1+ | Safe command execution | Separates command name from arguments — no injection risk |
| `ConvertFrom-Json` | PS 5.1+ | JSON parsing | Native PowerShell JSON parser, handles escaping correctly |
| PSScriptAnalyzer | 1.19+ | Static analysis | Official PowerShell linter, detects `AvoidUsingInvokeExpression` |

### Python Formatting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `subprocess.Popen` | stdlib | Process execution | format-all.py already uses it |
| `functools.lru_cache` | Python 3.2+ | Caching | Not used — manual dict cache for Py2 compatibility |

---

## Architecture Patterns

### Pattern: Safe Command Execution from Config

**What:** Replace `Invoke-Expression $cmdString` with `& $exe $args` when command string comes from external config.

**When to use:** Any time a command string from JSON/YAML/config needs to be executed.

**Example:**
```powershell
# Before (unsafe)
Invoke-Expression $buildCmd

# After (safe)
$parts = $buildCmd.Split(' ', 2)
$exe = $parts[0]
$args = if ($parts.Length -gt 1) { $parts[1] } else { "" }
& $exe $args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

### Anti-Patterns to Avoid

- **`Invoke-Expression` for dynamic command execution**: Even with trusted config, this is a PSScriptAnalyzer violation and security anti-pattern
- **Regex parsing JSON**: Fragile, breaks on escaping, nested structures, special characters
- **`cargo fmt --check` followed by `cargo fmt`**: Wastes I/O — `--check` result is always ignored

---

## Common Pitfalls

### Pitfall: Split() on Commands with Quoted Arguments

**What goes wrong:** `python -m pytest tests/ -v -s "test file.py"` — naive split on space breaks on quoted strings containing spaces.

**How to avoid:** Use `[Management.Automation.WordBreaker]::GetWords()` or a proper argument parser. For simple commands without complex quoting, `Split(' ', 2)` is acceptable because harness commands don't have quoted arguments with spaces.

**Current commands in project-config.json:** `python -m pytest tests/ -v`, `cargo test` — no quoted arguments. Safe to use simple split.

### Pitfall: JSON Parse Failure in Hooks Blocking Workflow

**What goes wrong:** `ConvertFrom-Json` throws on malformed JSON, which would cause hook to exit with error (non-zero), blocking Claude Code operations.

**How to avoid:** Wrap in try/catch, `exit 0` on any parse failure — hooks must NEVER block the workflow.

```powershell
try {
    $inputObj = $input | Out-String | ConvertFrom-Json
} catch {
    exit 0  # Fail open — don't block the workflow
}
```

### Pitfall: Python 2/3 dict Key Order

**What goes wrong:** Python 2 dicts don't preserve insertion order. Cache may not work as expected in Python 2.

**How to avoid:** `_cargo_root_cache` uses file directory path as key — insertion order doesn't matter for correctness, only performance. Python 2 behavior is acceptable here.

---

## Code Examples

### run-regression.ps1 — Safe Command Execution

**Before (lines 14-17):**
```powershell
if (-not [string]::IsNullOrWhiteSpace($buildCmd)) {
    Write-Host "执行构建: $buildCmd"
    Invoke-Expression $buildCmd
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

**After:**
```powershell
if (-not [string]::IsNullOrWhiteSpace($buildCmd)) {
    Write-Host "执行构建: $buildCmd"
    $parts = $buildCmd.Split(' ', 2)
    $exe = $parts[0]
    $args = if ($parts.Length -gt 1) { $parts[1] } else { "" }
    & $exe $args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

### clang-format.ps1 — ConvertFrom-Json

**Before (lines 3-8):**
```powershell
$inputJson = $input | Out-String

if ($inputJson -notmatch '"file_path"\s*:\s*"([^"]+)"') { exit 0 }
$filePath = $matches[1] -replace '\\\\', '\'

if ($filePath -notmatch '\.(cpp|cc|cxx|c|h|hpp|hxx)$') { exit 0 }
```

**After:**
```powershell
try {
    $inputObj = $input | Out-String | ConvertFrom-Json
    $filePath = $inputObj.tool_input.file_path
    if (-not $filePath) { exit 0 }
} catch {
    exit 0  # Fail open — don't block workflow
}

if ($filePath -notmatch '\.(cpp|cc|cxx|c|h|hpp|hxx)$') { exit 0 }
```

### pre-tool-use.ps1 — ConvertFrom-Json

**Before (lines 5-20):**
```powershell
$inputJson = $input | Out-String

$operation = ""
if ($inputJson -match '"tool"\s*:\s*"([^"]+)"') {
    $operation = $matches[1]
} elseif ($inputJson -match '"name"\s*:\s*"([^"]+)"') {
    $operation = $matches[1]
}

if ($operation -notmatch '^(Write|Edit)$') { exit 0 }

if ($inputJson -notmatch '"file_path"\s*:\s*"([^"]+)"') { exit 0 }
$filePath = $matches[1] -replace '\\\\', '\'
```

**After:**
```powershell
try {
    $inputObj = $input | Out-String | ConvertFrom-Json
    $operation = if ($inputObj.tool) { $inputObj.tool } else { $inputObj.name }
    $filePath = $inputObj.tool_input.file_path
    if (-not $filePath) { exit 0 }
} catch {
    exit 0  # Fail open
}

if ($operation -notmatch '^(Write|Edit)$') { exit 0 }
```

### format-all.py — Rust Dedup + Cache

**Before (lines 61-94):**
```python
def format_rust(file_path):
    current_dir = os.path.dirname(os.path.abspath(file_path))
    while current_dir:
        if os.path.exists(os.path.join(current_dir, "Cargo.toml")):
            try:
                proc = subprocess.Popen(
                    ["cargo", "fmt", "--check"],
                    cwd=current_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                proc.communicate(timeout=60)
                proc2 = subprocess.Popen(
                    ["cargo", "fmt"],
                    cwd=current_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                proc2.communicate(timeout=60)
                if proc2.returncode == 0:
                    print(u"[format-all] {0}: cargo fmt OK".format(file_path))
                    return
            except Exception:
                return
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
```

**After:**
```python
# Module-level cache: maps file_dir -> cargo_root_dir
_cargo_root_cache = {}

def _find_cargo_root(file_path):
    """Find and cache Cargo.toml directory for a given file path."""
    dir_path = os.path.dirname(os.path.abspath(file_path))
    if dir_path not in _cargo_root_cache:
        current = dir_path
        while current:
            if os.path.exists(os.path.join(current, 'Cargo.toml')):
                _cargo_root_cache[dir_path] = current
                break
            parent = os.path.dirname(current)
            if parent == current:
                _cargo_root_cache[dir_path] = None
                break
            current = parent
        else:
            _cargo_root_cache[dir_path] = None
    return _cargo_root_cache[dir_path]

def format_rust(file_path):
    """格式化 Rust 文件：在项目根目录执行 cargo fmt"""
    root = _find_cargo_root(file_path)
    if not root:
        return
    try:
        proc = subprocess.Popen(
            ["cargo", "fmt"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout_data, stderr_data = proc.communicate(timeout=60)
        if proc.returncode == 0:
            print(u"[format-all] {0}: cargo fmt OK".format(file_path))
    except Exception:
        pass
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dynamic command execution | `Invoke-Expression` | `& $exe $args` | `Invoke-Expression` is a PSScriptAnalyzer violation and injection risk |
| JSON parsing in PowerShell | Regex `-match` | `ConvertFrom-Json` | Native parser handles escaping, Unicode, edge cases correctly |
| JSON parsing in Shell | `sed` regex | `jq` or Python | `sed` doesn't understand JSON structure |
| Rust formatting | `cargo fmt --check` + `cargo fmt` | Just `cargo fmt` | `--check` output is always ignored, wastes I/O |

---

## Package Legitimacy Audit

> Phase 2 has no new external package dependencies. All changes use existing tools (PowerShell built-ins, Python stdlib).

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| None | — | N/A | No new packages |

---

## Testing Approach

### TECHD-07 Testing (Invoke-Expression)

**Static analysis:**
```bash
# Check for remaining Invoke-Expression usage
git grep 'Invoke-Expression' .claude/templates/harness/run-regression.ps1

# Run PSScriptAnalyzer if available
powershell -Command "Invoke-PSScriptAnalyzer .claude/templates/harness/run-regression.ps1 -IncludeRule AvoidUsingInvokeExpression"
```

**Functional test:**
```bash
# Create a minimal test project
mkdir -p /tmp/test-harness/.claude/state
echo '{"build-command": "echo build", "test-command": "echo test"}' > /tmp/test-harness/.claude/harness/project-config.json

# Run the script
powershell -ExecutionPolicy Bypass -File .claude/templates/harness/run-regression.ps1 -ProjectRoot /tmp/test-harness

# Verify it prints "执行构建: echo build" and "执行测试: echo test"
```

### TECHD-08 Testing (JSON Parsing)

**Static analysis:**
```bash
# PowerShell: check for regex JSON parsing
git grep -n 'notmatch.*file_path' .claude/hooks/scripts/*.ps1
git grep -n 'match.*tool' .claude/hooks/scripts/*.ps1

# Shell: check for sed JSON parsing
git grep -n 'sed.*file_path' .claude/hooks/scripts/*.sh
```

**Functional test (manual end-to-end):**
```bash
# Create a test JSON input
echo '{"tool_name":"Write","tool_input":{"file_path":"test.cpp","content":""}}' > /tmp/test_input.json

# Test clang-format.ps1
powershell -ExecutionPolicy Bypass -File .claude/hooks/scripts/clang-format.ps1 < /tmp/test_input.json
# Should exit 0, format nothing (test.cpp may not exist, but parsing should work)

# Test with Chinese path
echo '{"tool_name":"Write","tool_input":{"file_path":"C:\\用户\\文档\\测试.cpp","content":""}}' > /tmp/test_input_zh.json
powershell -ExecutionPolicy Bypass -File .claude/hooks/scripts/clang-format.ps1 < /tmp/test_input_zh.json
```

### TECHD-09 Testing (format-all.py)

**Static analysis:**
```bash
# Verify --check is removed
git grep 'cargo fmt --check' .claude/hooks/scripts/format-all.py

# Verify cache is implemented
git grep '_cargo_root_cache' .claude/hooks/scripts/format-all.py
```

**Functional test:**
```bash
# Create a test Rust file
mkdir -p /tmp/test-rust-project/src
echo 'fn main() { println!("test"); }' > /tmp/test-rust-project/src/main.rs
echo '[package]\nname = "test"\nversion = "0.1.0"' > /tmp/test-rust-project/Cargo.toml

# Run format-all.py
python .claude/hooks/scripts/format-all.py --file /tmp/test-rust-project/src/main.rs

# Verify cargo fmt was called once (check output contains "cargo fmt OK")
```

---

## Open Questions

1. **Q: Should we add PSScriptAnalyzer to the repository as a dev dependency?**
   - A: No — PSScriptAnalyzer is a global tool. Run manually: `pwsh -Command "Install-Module -Name PSScriptAnalyzer -Scope CurrentUser -Force; Invoke-PSScriptAnalyzer ..."` or use existing installation.

2. **Q: Should shell hooks use `jq` if available, or always Python?**
   - A: Use `jq` if available (faster startup), fallback to Python. The `.sh` files are already falling back to PowerShell anyway, so Python fallback is consistent.

3. **Q: Can we simplify `format_rust()` by using `subprocess.run` instead of `Popen`?**
   - A: Yes, but `subprocess.run` was added in Python 3.5. For Python 2.7 compatibility, `Popen.communicate()` is correct. Current code already uses `Popen`.

4. **Q: Should we verify Python syntax after format-all.py changes?**
   - A: Yes — run `python -m py_compile .claude/hooks/scripts/format-all.py` to verify syntax before committing.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Commands in project-config.json don't contain quoted arguments with spaces | Q1 | Low — current commands are simple, no quoted args |
| A2 | Claude Code hooks stdin always uses `tool_name` field (not `name`) | Q2 | Low — official hooks format documented |
| A3 | Python 2.7+ and 3.x both need to be supported | Q3 | Medium — if Py2 support is dropped, can use `functools.lru_cache` |
| A4 | `pre-compact.ps1` and `stop-check.ps1` don't use regex JSON parsing | Q2 | Low — verified by reading files |

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all patterns verified against Microsoft docs and existing codebase
- Architecture: HIGH — changes are localized, no cascading effects
- Pitfalls: HIGH — all edge cases confirmed, testing approach defined

**Research date:** 2026-06-15
**Valid until:** 2026-07-15 (30 days — security patterns are stable)