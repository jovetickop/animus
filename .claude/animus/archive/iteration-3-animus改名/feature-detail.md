# 功能详情

## T001 — 插件清单改名
- **描述**: 修改 `.claude-plugin/plugin.json` 中 `name: "animus"` → `"animus"`，所有命令名 `animus-xxx` → `animus-xxx`，描述文本更新。同时检查 `marketplace.json` 是否存在并更新。
- **验证命令**: `python -m json.tool .claude-plugin/plugin.json`

## T002 — .gitignore 路径更新
- **描述**: `.gitignore` 中 `.claude/animus/` → `.claude/animus/`
- **验证命令**: `grep "\.claude/animus/" .gitignore`

## T003 — 安装脚本改名
- **描述**: `templates/init-project.ps1` 中所有 "animus" → "animus"，".claude/animus/" → ".claude/animus/"，安装目录路径更新，GitHub URL 更新
- **验证命令**: `grep -n "animus" templates/init-project.ps1`（应返回空）

## T004 — 模板/运行时文件改名
- **描述**: `templates/animus/` 下所有文件中的 `animus` 路径引用和名称引用替换，含 `animus-history.jsonl` → `animus-history.jsonl`
- **涉及文件**: update-progress.ps1, coding-session.ps1, run-regression.ps1, init.ps1, show-status.py, features.json, project-config.json, task_plan.md, findings.md, plan-context.md, domain-lexicon.md, modules/*.ps1 等
- **验证命令**: `grep -rn "animus" templates/`

## T005 — 命令文件改名
- **描述**: 重命名 7 个命令 .md 并更新内容，重命名 animus-setup.ps1，更新 validate-features.ps1 和 check-consistency.ps1
- **文件名映射**:
  - `animus-setup.md` → `animus-setup.md`
  - `animus-plan.md` → `animus-plan.md`
  - `animus-review.md` → `animus-review.md`
  - `animus-handoff.md` → `animus-handoff.md`
  - `animus-continue.md` → `animus-continue.md`
  - `animus-archive.md` → `animus-archive.md`
  - `animus-debug.md` → `animus-debug.md`
  - `animus-setup.ps1` → `animus-setup.ps1`
- **验证命令**: `ls commands/animus-* 2>/dev/null | wc -l && grep -rn "animus" commands/`

## T006 — Hook 配置和脚本改名
- **描述**: hooks.json 中路径引用 + hooks/scripts/ 下 5 .ps1 + 5 .sh 中 `.claude/animus/` 路径和 `animus` 日志前缀。含 `animus-history.jsonl` → `animus-history.jsonl` 路径更新
- **验证命令**: `grep -rn "animus" hooks/`

## T007 — Agent 定义改名
- **描述**: agents/ 下 22 个 .md 文件中 `.claude/animus/` → `.claude/animus/`，命令名 `/animus-xxx` → `/animus-xxx`，插件描述更新。含 `animus-history.jsonl` → `animus-history.jsonl` 引用更新
- **验证命令**: `grep -rn "animus" agents/`

## T008 — 技能文件改名
- **描述**: skills/ 下文件中的 `animus` 引用更新，含 `animus-history.jsonl` → `animus-history.jsonl`
- **验证命令**: `grep -rn "animus" skills/`

## T009 — Python 脚本改名
- **描述**: scripts/ 下 .py 文件中 `animus` 路径引用和字符串替换。含 `animus-history.jsonl` → `animus-history.jsonl` 文件名和路径引用更新
- **验证命令**: `grep -rn "animus" scripts/`

## T010 — 规则文件改名
- **描述**: rules/ 下 13 个 .md 文件中 `animus` 引用和路径更新，含 `animus-history.jsonl` → `animus-history.jsonl`
- **验证命令**: `grep -rn "animus" rules/`

## T011 — 文档/README 改名
- **描述**: README.md 全面更新（项目名、命令名、路径、GitHub 链接）+ docs/ 下 3 个文件。GitHub URL 中 animus 改为 animus
- **验证命令**: `grep -n "animus" README.md docs/`

## T012 — CLAUDE.md 更新
- **描述**: CLAUDE.md 中约 80+ 处 `animus` 引用全部替换
- **验证命令**: `grep -n "animus" CLAUDE.md`

## T013 — 整体兜底扫描
- **描述**: grep 全库扫描 + plugin-validator + JSON 语法检查 + PS/Python 语法检查
- **验证命令**: 
  ```
  grep -rn "animus" . --include="*" --exclude-dir=.git 2>/dev/null | grep -v "node_modules" | head -40
  python -m json.tool .claude-plugin/plugin.json
  python -m py_compile scripts/*.py  # 各脚本逐一检查
  powershell -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw 'templates/init-project.ps1'), [ref]$null); 'ok'"
  ```

## T014 — harness 概念词全局改名
- **描述**: 全局替换 `animus-history.jsonl` → `animus-history.jsonl`，涉及 agents/、templates/、hooks/、scripts/、commands/、rules/、skills/ 中所有路径和文件名引用。概念性描述中的 "harness" 也改为 "animus"
- **验证命令**: `grep -rn "animus-history.jsonl" agents/ templates/ hooks/ scripts/ commands/ rules/ skills/`

## T015 — templates/animus/ 目录重命名
- **描述**: 将 `templates/animus/` 整个目录重命名为 `templates/animus/`。注意：hooks/scripts/ 中的路径引用（`templates/animus/project-config.json`）也需要同步更新
- **验证命令**: `ls templates/animus/ 2>/dev/null && grep -rn "templates/harness" hooks/`

## T016 — .claude/animus/ 运行时目录重命名
- **描述**: 将 `.claude/animus/` 整个目录树重命名为 `.claude/animus/`。注意同步更新所有外部引用该路径的文件。含 archive/、docs/ 子目录及 .gitignore 中的引用。注意此时仓库自身的运行时状态文件会丢失路径，需要同步处理
- **验证命令**: `ls .claude/animus/ 2>/dev/null && grep -rn "\.claude/animus" --include="*.md" --include="*.ps1" --include="*.py" --include="*.sh" --include="*.json" .`

## T017 — Git 分支/工作空间清理
- **描述**: 将 worktree-animus-* 分支重命名为 worktree-animus-*（git branch -m），清理 .git/refs/heads/ 和 .git/logs/refs/heads/ 中的旧引用。删除旧 worktree 目录
- **验证命令**: `git branch -a | grep -i harness`（应返回空）

## T018 — Archive 档案数据更新
- **描述**: 更新 `.claude/animus/archive/iteration-1-*` 和 `iteration-2-*` 中的 features.json、feature-detail.md、iteration-summary.md 等文件中的 animus 引用。包括命令名、路径、animus-history.jsonl 文件名等
- **验证命令**: `grep -rn "animus" .claude/animus/archive/`

## T019 — GitHub URL 统一更新
- **描述**: 将 `animus` GitHub URL（如 `github.com/jovetickop/animus`）统一改为 `github.com/jovetickop/animus`。涉及 plugin.json（homepage）、README.md、init-project.ps1 等文件
- **验证命令**: `grep -rn "animus" plugin.json README.md templates/init-project.ps1`（应返回空）
