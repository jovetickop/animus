# Stack Research

**Domain:** Claude Code 技能插件 / 多语言代码审查编排框架 (harness-cc)
**Researched:** 2026-06-14
**Confidence:** HIGH

## Executive Summary

本文件研究四种关键技术维度的当前最佳实践：(1) PowerShell 脚本编码策略，(2) 多语言代码审查编排工具，(3) Python 2/3 兼容脚本编写，(4) Claude Code / AI Agent 插件开发模式。研究结果是针对 harness-cc 项目的技术债务修复（TECHD-01 至 TECHD-11）和后续架构决策的直接输入。

核心结论：
- **编码方向 UTF-8 with BOM 已验证正确**，这是 PowerShell 5.1 跨平台场景的行业标准选择
- reviewdog 的 errorformat + rdjson 模式比当前 format-all.py 的自定义分发模式更成熟，建议引入作为备选方案
- Python 2/3 双兼容的 `from __future__` + `sys.version_info` 模式仍然正确，无需改用第三方库
- 当前三层架构（技能→命令→Agent）符合 Claude Code 推荐的插件模式，但 documentation gap 需要填补

## Recommended Stack

### 1. PowerShell 编码策略

| 编码方案 | 版本/场景 | 用途 | 为什么推荐 |
|----------|----------|------|----------|
| **UTF-8 with BOM (EF BB BF)** | PowerShell 5.1 + 7.x 跨平台 | .ps1/.psm1/.psd1 源文件编码 | 唯一被两个 PowerShell 版本同时正确识别的编码；Windows PowerShell 5.1 无 BOM 会误判为 ANSI (Windows-1252)；PowerShell 7+ 原生识别 BOM |
| **UTF-8 without BOM** | PowerShell 7+ 专属 | 纯 PS7+ 环境的脚本、Unix 平台 | 如果放弃 PS5.1 支持可用；Unix 工具（grep/sed/awk）不会误读 BOM |
| **显式 -Encoding utf8** 参数 | 所有文件输出操作 | 文件 IO 一致性 | `Out-File` / `Set-Content` 默认编码在两个 PowerShell 版本中不同（5.1: UTF-16LE, 7+: UTF-8），显式指定消除歧义 |

**不推荐的选择：**

| 避免 | 为什么 | 使用替代 |
|------|-------|---------|
| **UTF-16LE (BOM: FFFE)** | Git diff 不可读（`\0` 填充）、文件体积大 2 倍、Claude Code 读取为乱码、历史已证明中文注释损坏 (commit 628f02c) | **UTF-8 with BOM** |
| **UTF-8 without BOM** (PS5.1 场景下) | Windows PowerShell 5.1 会将其作为 ANSI (e.g. Windows-1252) 解析，非 ASCII 字符乱码 | **UTF-8 with BOM** |
| **ANSI / 系统默认编码** (e.g. Windows-1252, GBK) | 不可移植，依赖系统区域设置 | **UTF-8 with BOM** |
| **依赖 `Out-File` 默认编码** | 5.1 输出 UTF-16LE, 7+ 输出 UTF-8 without BOM，行为不一致 | 显式 `-Encoding utf8` 或 `$PSDefaultParameterValues['*:Encoding']='utf8'` |

**选择方案对比：**

| 标准 | UTF-8 with BOM | UTF-8 without BOM | UTF-16LE |
|------|----------------|-------------------|-----------|
| PowerShell 5.1 兼容 | 是 | 否（ANSI 误判） | 是 |
| PowerShell 7+ 兼容 | 是 | 是 | 是 |
| Git diff 可读性 | 良好 | 良好 | 差（填充 `\0`） |
| 文件体积（英文为主） | ~100% | ~100% | ~200% |
| Unix 工具友好 | 部分（BOM 可能干扰） | 是 | 否 |
| Claude Code 读取 | 良好 | 良好（7+）/ 差（5.1 下） | 差 |
| VS Code 默认 | 需配置 | 是（default） | 否 |

### 2. 多语言代码审查编排工具

| 工具 | 类型 | 语言 | 适用场景 | 为什么 / 不推荐 |
|------|------|------|---------|----------------|
| **reviewdog** | 轻量编排层 | Go | CI 中编排任意 linter/formatter，PR 评论 | 推荐用于 CI/CD 集成；errorformat + rdjson 输入模式成熟；diff-aware 过滤减少噪音 |
| **format-all.py (当前)** | 自定义分发脚本 | Python (std lib) | PostToolUse hook 内多语言格式化 | 推荐继续使用（零依赖、PS 5.1 兼容）；可借鉴 reviewdog rdjson 格式改进输出标准化 |
| **MegaLinter** | 全量分析平台 | Python | 跨 50+ 语言的全量代码质量检查 | 对 harness-cc 场景过重（Docker 依赖、100+ linter 预装）；可参考其 descriptor-driven 设计的模块化思路 |
| **SonarQube** | 企业级分析平台 | Java | 团队级持续质量门禁 | 对插件工具链场景过重（需要 Server + DB + Scanner）；不适合嵌入 Claude Code hook；可参考其 Sensor 模式 |

**不对 reviewdog/SonarQube 做二选一 —— 它们解决不同问题、在不同层级工作：**

| 维度 | reviewdog | MegaLinter | SonarQube |
|------|-----------|------------|-----------|
| 部署形态 | Go 单二进制 | Docker 容器 | Server + DB + Scanner |
| 启动时间 | ~毫秒 | ~秒（容器） | ~分钟（全套） |
| 适合嵌入 hook | 是 | 否（太重） | 否 |
| 多语言处理 | 通过 errorformat 适配任意工具 | 内置 100+ linter descriptor | 通过语言插件扩展 |
| diff-aware 过滤 | 是（核心特性） | 是（通过 REPORT_OUTPUT_FOLDER） | 是（PR analysis 模式） |
| 输出格式 | rdjson/rdjsonl/checkstyle/SARIF | SARIF/自定义 | SonarQube 内部格式 |

**结论：** reviewdog 的 rdjson 格式和 errorformat 模式值得参考，但 harness-cc 当前的 format-all.py（仅 200 行 Python，零依赖）对于 PostToolUse hook 场景是更合适的选择——它轻量、无启动延迟、不引入新的运行时依赖。

### 3. Python 2/3 双兼容方案

| 技术 | 用法 | 为什么推荐 |
|------|------|-----------|
| `from __future__ import ...` | `print_function`, `division`, `unicode_literals`, `absolute_import` | 标准库内置，零依赖；让 Py2 行为尽可能接近 Py3 |
| `sys.version_info` 守卫 | `if sys.version_info[0] >= 3:` 分支判断 | 当 `__future__` 无法覆盖的行为差异时使用 |
| `try/except ImportError` 别名 | 处理重命名模块（`ConfigParser` → `configparser` 等） | Py2 → Py3 模块名变化的标准兼容模式 |
| `io.open()` | 文件读写，带 `encoding=` 参数 | Py2 和 Py3 行为一致；`from io import open` |
| **避免 `six` 或 `future` 第三方库** | 不使用 `pip install six` | 当前仓库约束是零第三方 Python 依赖，这是正确的；标准库模式已足够 |

**关键模块名变化对照表：**

| Python 2 | Python 3 | 兼容写法 |
|----------|----------|----------|
| `ConfigParser` | `configparser` | `try: import configparser; except ImportError: import ConfigParser as configparser` |
| `Queue` | `queue` | 同上模式 |
| `urllib2` | `urllib.request` | 同上模式 |
| `cPickle` | `pickle` | `try: import cPickle as pickle; except ImportError: import pickle` |
| `StringIO.StringIO` | `io.StringIO` | `from io import StringIO` (优先; Py2 fallback 需额外处理) |

**重要决策：** 维持零第三方 Python 依赖的策略是正确的。`six` 库虽然方便，但新增一个运行时依赖的管理成本超过其收益——当前代码库中的 `__future__` + `sys.version_info` 模式已足够覆盖所有必要场景。

### 4. Claude Code 插件 / Agent 开发模式

| 模式 | 用途 | 性能成本 | 推荐使用场景 |
|------|------|---------|-------------|
| **CLAUDE.md** | 持久上下文，每会话加载 | 每次请求 | 全局规则、编码规范、安全约束 |
| **Skills** | 按需加载的指令集 | 低（仅描述加载） | 工作流指导（如 `/harness-cc` 入口） |
| **Slash Commands** | 用户调用的规范化命令 | 低 | 3 个编排命令（setup/plan/review） |
| **MCP Servers** | 外部服务集成 | 低（按需调用） | filesystem/git/memory/linear |
| **Subagents** | 隔离执行上下文 | 中（独立实例） | 多语言并行实现/审查任务 |
| **Hooks** | 生命周期事件触发器 | 可配置 | 格式化、编码转换、备份、状态检查 |
| **Plugins** | 上述所有元素的打包层 | 各异 | 分发到目标项目的完整插件 |

**当前三层架构评价：** 当前的 `SKILL.md → commands/ → agents/ + rules/` 分层完全符合 Anthropic 官方推荐模式。与 community 同类项目（serpro69/claude-toolbox, sjnims/plugin-dev）相比，harness-cc 的状态机引擎是独有优势——community 项目多停留在 skill/command 编排层，未实现状态化进度跟踪。

**已知差距（需要填补）：**
- `.claude-plugin/plugin.json` 清单文件缺失（当前以 `SKILL.md` 作为入口，但无官方 plugin manifest）
- 缺少 plugin 级别文档说明安装/卸载/版本管理
- 无 `-v` 或 `--version` 命令展示插件的当前版本和更新日志

## Supporting Libraries

| Library | Purpose | When to Use | 评价 |
|---------|---------|-------------|------|
| **reviewdog** | 编排任意 linter 到 PR 评论 | 目标项目的 CI/CD 中使用 | 对 hook 内使用太重；可在 format-all.py 之后增加 rdjson 输出格式选项 |
| **ruff** | Python 快速 lint + format | 替代 black + autopep8（Python 3 项目） | 但当前仓库必须兼容 Python 2.7，不能使用 |
| **pre-commit** | Git hook 编排 | 目标项目的本地开发流程 | 不能嵌入 Claude Code hooks；两种 hooks 系统解决不同问题 |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `six` / `python-future` 第三方库 | 零依赖策略已经工作，新增依赖管理成本 | `from __future__` + `sys.version_info` 标准模式 |
| UTF-16LE for .ps1 files | Git diff 不可读、体积加倍、已造成中文乱码 (TECHD-01) | UTF-8 with BOM |
| `Invoke-Expression` | 命令注入安全风险 (CONCERNS 风险 #2) | `& $cmd 2>&1` 或 `Start-Process -NoNewWindow` |
| 正则解析 JSON（PostToolUse hook 中） | 脆弱、JSON 转义字符导致断裂 (CONCERNS 维护性 #2) | `$input \| ConvertFrom-Json`（使用 PowerShell 原生 JSON 解析器） |
| MegaLinter/SonarQube 嵌入 PostToolUse hook | 启动延迟太长（秒/分钟级），阻塞整个工具链 | format-all.py（~毫秒启动）或 reviewdog（单二进制） |
| `utf8` 无参数指定（依赖隐式行为） | PS 5.1 和 7+ 对 `-Encoding utf8` 默认行为不同（一个有 BOM 一个无） | 始终显式指定 `-Encoding utf8BOM` 或 `-Encoding utf8NoBOM` 以消除歧义 |

## Stack Patterns by Variant

**若继续支持 PowerShell 5.1（必须）：**
- 源文件编码：**UTF-8 with BOM**（已被 PROJECT.md 确认）
- 文件输出操作：始终指定 `-Encoding utf8`（在 5.1 下等效于 utf8BOM）
- 避免使用 PS 7+ 专属特性（`Ternary` 运算符 `? :`、`ForEach-Object -Parallel`、`Get-SecureRandom` 等）
- 设置 `$PSDefaultParameterValues['*:Encoding']='utf8'` 作为防御性措施

**若目标项目使用 GBK 编码（如中国 Windows 工程软件）：**
- 维持当前的 encoding-bridge.py + hooks 方案（已验证工作）
- 明确 `project-config.json` 中 `"encoding": ""` 的含义：空值 = UTF-8，不触发编码桥接
- 添加文档说明该字段的行为契约

**若 Python 脚本不需要支持 Python 2（理论上可放弃）：**
- 移除所有 `from __future__` 导入
- 使用 f-strings 替代 `.format()`
- 使用 `pathlib` 替代 `os.path`
- 考虑改用 `ruff` 替代 `black` + `autopep8` 双降级
- **但目前不宜放弃**——目标项目可能运行在仅安装 Python 2.7 的遗留 Windows 系统上

## Version Compatibility

在 harness-cc 场景下（本仓库无构建步骤，是运行时解释的插件），版本兼容性问题集中在运行时环境而非包依赖：

| 技术 | 兼容版本 | 注意事项 |
|------|---------|---------|
| PowerShell 运行时 | **5.1** (最低), **7.x** (推荐) | `$PSVersionTable.PSVersion` 可在脚本中检测版本；PS 5.1 无 `? :` 三元和并行 foreach |
| Python 运行时 | **2.7+**, **3.x** (正式) 但在 2026 年 Py2 事实上已不可靠 | 当前 `from __future__` 模式在 `sys.version_info` < (2,7) 时会失败，但 2.7 是最低可接受版本 |
| Bash / Shell | 任意 POSIX shell | hooks 中的 `.sh` 文件必须 LF 换行（当前存在 CRLF 问题，标记为 TECHD-02） |
| .gitattributes | 所有 Git 版本 | 建议添加 `*.ps1 text eol=lf` 确保 LF 一致性 |

## Claude Code Plugin 架构对比

| 维度 | harness-cc (当前) | serpro69/claude-toolbox | sjnims/plugin-dev |
|------|-------------------|------------------------|-------------------|
| **插件入口** | SKILL.md (入口) | SKILL.md (入口) | SKILL.md (入口) |
| **状态化进度** | 是（状态机引擎） | 否 | 否 |
| **多语言支持** | 6 种语言 + Agent 定义 | 6 种语言 + workspace 配置 | 仅开发工具（plugin-dev 自身） |
| **Hooks 系统** | 4 个钩子（完整） | 无 | 无 |
| **MCP 集成** | 4 个服务器 | 自定义服务器 | 无 |
| **Plugin Manifest** | 无 `.claude-plugin/` | 无 | 有（示范架构） |
| **项目初始化** | `init-project.ps1` + 自动检测 | 无 | 8-phase 引导流程 |
| **CI 集成** | 通过 hooks | 无 | 仅验证脚本 |
| **社区活跃度** | 私有（本仓库） | 开源 | 开源 |

**核心差异点：** 其他 community 项目关注 skill/command 编排和 LLM prompt 优化，harness-cc 的差异化价值在于**状态化进度跟踪**和**可验证的工作流契约**（Oracle 验证、依赖顺序、状态转移矩阵）。这个差异应该保持。

## 针对 TECHD 项目的具体建议

### TECHD-01 (编码统一)
**推荐：** UTF-8 with BOM。将 `templates/harness/` 和 `commands/` 目录下的 7 个 UTF-16LE .ps1 文件转换为 UTF-8 with BOM。
**验证方式：** `file --mime-encoding *.ps1` 或 powershell `[System.Text.Encoding]::Default.GetString([System.IO.File]::ReadAllBytes($path))`
**风险提示：** BOM 对 Unix shebang 脚本可能产生干扰——但 .ps1 文件没有 shebang，所以安全。

### TECHD-07 (Invoke-Expression 替换)
**推荐：** 用 `& $cmd 2>&1` 或 `Start-Process -NoNewWindow -FilePath $exe -ArgumentList $args -Wait -RedirectStandardOutput $log` 替换。
**参考：** Microsoft 安全公告明确指出 `Invoke-Expression` 用于动态执行不可信字符串是安全风险。

### TECHD-08 (正则解析 JSON 替换)
**推荐：** 用 `$input | ConvertFrom-Json` 替换 regex 解析。
**注意：** `ConvertFrom-Json` 在 PS 5.1 和 PS 7+ 都可用，无需担心兼容性。

### TECHD-11 (文档补充)
**推荐补充文档项：**
1. UTF-16LE 历史原因说明（如果有）、转换策略、对 Git 历史的影响
2. `templates/state/` 下三个 JSON 文件的角色和生命周期
3. 钩子调试方法（设置 `$env:HOOK_DEBUG=true` 临时启用 stderr 输出）
4. `project-config.json` 中 `encoding` 字段的行为契约
5. 插件版本管理和更新流程

## Sources

- Microsoft Learn: "Configuring PowerShell Default Output Encoding" — 编码策略官方文档
- Microsoft Learn: "How to Write a PowerShell Module Manifest" — 模块清单最佳实践
- Microsoft Learn: "PowerShell module authoring considerations" — 性能优化指南
- GitHub: reviewdog/reviewdog — 多语言代码审查编排工具
- GitHub: oxsecurity/megalinter — 多语言 linting 平台架构
- SonarQube Documentation 2025.4 LTA — 架构概述
- Claude Code Official Documentation (code.claude.com) — Hooks, Plugins, Skills 官方文档
- Anthropic: github.com/anthropics/claude-code — 官方插件参考实现
- GitHub: serpro69/claude-toolbox — Community 插件模式
- GitHub: sjnims/plugin-dev — 插件开发工具包
- Python Official Porting Guide — Python 2→3 兼容模式
- Stack Overflow / Microsoft Docs — UTF-8 BOM PowerShell 跨版本注意事项
- Claude Blog: "How to configure hooks" — hooks 最佳实践指南

## Confidence Assessment

| 维度 | 置信度 | 理由 |
|------|--------|------|
| **PowerShell 编码策略** | HIGH | Microsoft 官方文档 + 多个已验证的正确性证据（CONCERNS.md 编码问题已确认） |
| **多语言编排工具选择** | MEDIUM | reviewdog 的 rdjson 格式对未来有用但当前 format-all.py 方案更合适；决策依赖于"零依赖"约束是否长期保持 |
| **Python 2/3 兼容** | HIGH | Python 已正式 EOL 但标准兼容模式文档完善；当前模式已验证工作 |
| **Claude Code 插件架构** | MEDIUM | 官方文档 + community 项目验证了当前架构方向正确；但缺少 plugin manifest 和 version 管理 |
| **跨平台 BOM 策略** | HIGH | PowerShell 5.1 + 7+ 已知行为；CRLF→LF 问题 (TECHD-02) 也需同步处理 |

## Gaps to Address

1. **SonarQube vs reviewdog 的 diff-aware 对比** 需要更深入的比较——当前信息不够以决定是否在 CI 场景推荐 reviewdog 替代 SonarQube
2. **Claude Code Plugin Manifest 规范** 当前官方文档对 `.claude-plugin/plugin.json` 的 schema 描述不够完整，社区实现仅供参考
3. **PowerShell 7+ exclusive 的迁移路径** 当前约束为必须兼容 PS 5.1；未来若放弃 5.1 支持，需重新评估编码策略（可改用 UTF-8 without BOM 简化 Unix 兼容性）
4. **format-all.py 的 rdjson 输出扩展** 如果引入此功能，需要定义如何将格式化结果传递给 Claude Code（当前通过 hook stdout）
5. **Git 工作流中的 encoding diff 管理** UTF-16LE → UTF-8 with BOM 转换会导致 Git blame/annotate 大量第一行标记为本次转换；建议通过 `.gitattributes` 的 `working-tree-encoding` 或一次性转换 commit + .git-blame-ignore-revs 管理

---
*Stack research for: harness-cc (Claude Code skill plugin / multi-language code review orchestration framework)*
*Researched: 2026-06-14*
