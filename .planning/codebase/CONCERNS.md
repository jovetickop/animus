# 关注点与风险分析

_生成日期：2026-06-14_

## 技术债务

### 1. 脚本编码不一致（严重）

**描述：** 同一仓库内 PowerShell 脚本使用了两种编码格式，导致 Git 差异显示异常、代码审查困难、跨平台兼容性问题。

- `templates/harness/` 目录（`update-progress.ps1`, `run-regression.ps1`, `coding-session.ps1`, `init.ps1`）和 `commands/` 目录（`check-consistency.ps1`, `harness-code-setup.ps1`, `validate-features.ps1`）为 **UTF-16LE** 编码（BOM: `FFFE`）
- `hooks/scripts/` 目录（`clang-format.ps1`, `pre-tool-use.ps1`, `pre-compact.ps1`, `stop-check.ps1`）和 `templates/init-project.ps1` 为 **UTF-8** 编码

**影响：**
- Git diff 无法正确显示变更（显示为每字节间填充 `\0`）
- 中文注释在 UTF-16LE 文件中变为不可读的二进制内容（已被历史提交证实，commit `628f02c`）
- Claude Code 读取 UTF-16LE 文件时内容呈现为乱码
- 文件体积比 UTF-8 大 2 倍

**严重程度：** 高

**修复方向：** 统一为 UTF-8 with BOM 编码，因为 PowerShell 5.1 和 7.x 均支持；对外发布时在 `init-project.ps1` 中处理目标项目的编码适配。

### 2. 换行符不一致

**描述：** 部分脚本混用 CRLF 和 LF 换行符。

- `.claude/hooks/scripts/` 下的 `.sh` 脚本（`pre-compact.sh`, `pre-tool-use.sh`, `stop-check.sh`）使用 CRLF 换行符（Windows 风格），但 Shell 脚本应该在 Unix 系统使用 LF
- `templates/harness/update-progress.ps1` 同时包含 CRLF 和 LF

**影响：**
- Shell 脚本在 Linux/Mac 下运行时，CR 可能被解释为命令的一部分，导致执行失败
- 破坏 `.gitattributes` 一致性

**严重程度：** 中

### 3. features.json 状态文件路径存在双重查找逻辑

**描述：** 多个脚本同时支持 `.claude/harness/features.json` 和 `.claude/state/features.json` 两个路径。

涉及文件：`pre-compact.ps1`, `pre-compact.sh`, `stop-check.ps1`, `stop-check.sh`, `pre-tool-use.ps1`, `pre-tool-use.sh`, `session-catchup.py`

**影响：**
- 状态文件位置不唯一，增加维护负担
- 备份脚本若只备份一个路径，可能导致数据不一致
- `features.json` 模板有三个版本：`templates/state/features.json`（`tasks` 格式, 无 `parallel_group`）、`templates/state/features.active.json`（有 `parallel_group` 字段）、`templates/state/features.archive.json`（空 `tasks` 数组）

**严重程度：** 中

**修复方向：** 确定标准路径为 `.claude/state/features.json`，移除对旧的 `.claude/harness/` 路径的支持。

### 4. UTF-16LE 脚本内的中文注释已损坏

**描述：** 由于 UTF-16LE 编码文件的读取问题，`templates/harness/update-progress.ps1` 内部的中文字符串内容（如状态摘要、错误消息）在当前工作流中显示为乱码。例如第 100-104 行的状态摘要字符串：

```
"passed"  -> "�����Ǐ"     (应为 "通过")
"failed"  -> "����1Y%"     (应为 "失败")
```

**影响：**
- AI 工作流无法理解脚本输出的中文状态提示
- 报告生成的内容可能混入乱码
- 用户看到的控制台输出包含乱码

**严重程度：** 高

### 5. 模板状态目录与运行时状态目录混淆

**描述：** `.claude/templates/state/` 包含三个 JSON 模板文件，但其用途不明确——它们是安装到目标项目的模板，还是仓库自身的状态文件？

- `features.json` — 包含示例任务和 `verify_config` 对象格式结构
- `features.active.json` — 使用 `tasks` 数组格式（含 `parallel_group`）
- `features.archive.json` — 仅空数组

`features.json` 实际应该由 `init-project.ps1` 从 `templates/harness/` 复制到目标项目的 `.claude/state/`，但 `templates/state/` 下的文件作为什么用途不清晰。

**严重程度：** 中

### 6. `format-all.py` 中的 Rust 格式化逻辑低效

**描述：** `hooks/scripts/format-all.py` 第 68-84 行先执行 `cargo fmt --check`（仅检查不修改），忽略结果后立即执行 `cargo fmt`（实际格式化）。`--check` 调用没有任何作用，浪费 I/O。

**影响：**
- 每次写入 Rust 文件都触发两次 `cargo fmt`，在大型 Rust 项目中浪费数秒
- `--check` 的退出码被完全忽略

**严重程度：** 低

---

## 潜在风险

### 1. 跨平台 Shell 脚本兼容性风险

**描述：** `.claude/hooks/scripts/` 下的 `.sh` 脚本虽然设计了 bash/PowerShell 双路径降级（`hooks.json` 中 `bash ... || powershell ... || exit 0`），但存在以下问题：

- Shell 脚本文件使用 CRLF 换行，在 Unix 下的 bash 中会解析失败
- `pre-tool-use.sh` 使用 `sed` 解析 JSON，当 JSON 中有转义字符或换行时会断裂（第 9、21 行）
- `run-regression.ps1` 使用 `Invoke-Expression` 执行来自配置文件的外部命令，存在命令注入风险

**严重程度：** 高

### 2. `Invoke-Expression` 安全风险

**描述：** `templates/harness/run-regression.ps1` 第 16、24、40 行使用 `Invoke-Expression` 执行从 `project-config.json` 或 `features.json` 中读取的命令字符串。

```powershell
Invoke-Expression $buildCmd
Invoke-Expression $testCmd
```

这些命令来自于 JSON 配置文件，如果配置被恶意修改或含有未转义的特殊字符，可能导致任意代码执行。

**严重程度：** 中（在目标项目的受控环境中风险较低，但需注意）

### 3. `init-project.ps1` 硬编码用户技能路径

**描述：** `templates/init-project.ps1` 第 50-51 行硬编码了用户技能目录路径：

```powershell
$UserSkillRoot = Join-Path $env:USERPROFILE ".claude\skills\harness-cc"
```

如果用户安装技能到其他目录（如团队共享目录或多用户环境），脚本无法定位技能源文件。

**严重程度：** 中

### 4. `project-config.json` 默认配置包含非通用命令

**描述：** `templates/harness/project-config.json` 的默认值中包含了特定的 Python 后端/前端框架命令：

- `configure-command`: `pip install -r requirements.txt`
- `build-command`: `python -m pytest tests/ -v`
- `test-command`: `python -m pytest tests/ -v`
- `run-command`: `uvicorn app.main:app --reload`

这些值对于非 Python 项目是误导性的，自动检测逻辑可能错过正确的项目类型。

**严重程度：** 低

---

## 安全关注点

### 1. MCP 服务器配置中的 API 密钥环境变量

**描述：** `.claude/templates/.mcp.json` 第 44 行配置了 Linear API 密钥的 env 变量：

```json
"LINEAR_API_KEY": "${env:LINEAR_API_KEY}"
```

这属于模板文件，本身不包含密钥值。但该文件会被复制到目标项目的根目录。如果用户不小心提交包含实际密钥值的 `.mcp.json` 到公开仓库，会造成凭证泄露。

**当前状态：** 模板本身安全。但需在文档中强调不提交 `.mcp.json` 到公开仓库。

### 2. 钩子脚本可能泄露文件路径到输出

**描述：** `pre-tool-use.ps1`（第 40 行）和 `clang-format.ps1`（第 40 行）将文件路径写入控制台输出：

```
Write-Host "[encoding-bridge] re-encoded to GBK: $filePath"
```

这属于信息泄露的低风险问题，但 Claude Code 的 hook 输出会被记录到 session 日志。

**严重程度：** 低

---

## 维护性关注点

### 1. `update-progress.ps1` 规模过大

**描述：** 状态机核心脚本 `templates/harness/update-progress.ps1` 共 424 行，同时承担了以下职责：
- 参数验证和目标查找
- 状态转换校验（5 种状态的完整转换矩阵）
- Oracle 验证执行（构建/测试命令运行）
- 报告生成（Markdown 格式）
- 进度日志更新
- Git 自动提交

**建议：** 拆分为 `validate-transition.ps1`、`oracle-runner.ps1`、`report-generator.ps1` 等独立模块。

### 2. 手动参数解析模式

**描述：** `hooks/scripts/clang-format.ps1` 和 `pre-tool-use.ps1` 使用正则表达式从 JSON stdin 提取字段（第 5-6 行）：

```powershell
$inputJson = $input | Out-String
if ($inputJson -notmatch '"file_path"\s*:\s*"([^"]+)"') { exit 0 }
```

这比使用 `ConvertFrom-Json` 更脆弱，当 JSON 结构变化（如字段顺序、转义字符、嵌套结构）时可能解析失败。

**严重程度：** 中

**建议：** 使用 `$input | ConvertFrom-Json` 替代正则解析。

### 3. 钩子脚本的降级路径复杂

**描述：** `hooks.json` 为每个事件注册了 bash/PowerShell 双路径（如第 8 行）：

```json
"bash \"...clang-format.sh\" 2>/dev/null || powershell ...clang-format.ps1 2>/dev/null || exit 0"
```

三重短路逻辑使调试困难。当任一分支失败时，错误信息被 `/dev/null` 吞噬，无法排查。

**严重程度：** 低

### 4. `format-all.py` 的文件分发逻辑不够健壮

**描述：** `hooks/scripts/format-all.py` 中 `format_rust` 函数每次运行时都从当前文件路径向上遍历查找 `Cargo.toml` 目录，导致对一个 Rust 项目中的 10 个文件做写操作时，会触发 10 次全项目 `cargo fmt`。

**建议：** 缓存查找 `Cargo.toml` 目录的结果。

---

## 已观察到的反模式

### 1. 相同的路径查找逻辑重复 6 次

**描述：** 在多个脚本中重复实现了"从当前文件向上遍历目录查找 `.claude/state/features.json`"的逻辑：

- `pre-tool-use.ps1`（第 56-68 行）
- `pre-tool-use.sh`（第 28-41 行）
- `pre-compact.ps1`（第 16-23 行）
- `pre-compact.sh`（第 10-17 行，但用 `cd` 方式）
- `stop-check.ps1`（第 6-12 行，用 `$PSScriptRoot/../../..`）
- `stop-check.sh`（第 7-9 行，用 `cd` 方式）
- `clang-format.ps1`（第 17-33 行，额外查找 `project-config.json`）

**影响：** 查找逻辑共 6 种变体，部分查找 `features.json`，部分查找 `project-config.json`，路径基准各不相同。修改其中一个容易遗漏其他。

### 2. `format-all.py` 错误处理过于宽泛

**描述：** 所有格式化函数中的异常处理都是 `except Exception: return False`，吞噬了所有错误信息。当格式化工具缺失时，无声失败也不做日志。

### 3. 状态机在 `completed` 状态处理上过度宽松

**描述：** `update-progress.ps1` 第 264-265 行允许从 `pending` 直接到 `completed`：

```powershell
if ($currentStatus -eq "pending") {
    # completed 允许直接从 pending 跳过
```

这绕过了工作流中"必须有构建/测试证据"的硬规则（由 CLAUDE.md 状态机核心规则要求）。

---

## 知识/文档缺口

### 1. UTF-16LE 编码策略未文档化

`CLAUDE.md` 中未说明为什么部分文件是 UTF-16LE、哪些文件应保持此编码、修改时如何处理。新维护者容易意外转换编码导致 Git 差异剧增。

### 2. `templates/state/` 目录角色的文档缺失

`templates/state/` 下的 `features.json`、`features.active.json`、`features.archive.json` 三者的用途和区别没有文档说明。从命名看可能是"状态模板"、"活跃任务模板"、"归档用空模板"的区分，但无法确认。

### 3. 钩子脚本调试方式未文档化

当 `hooks.json` 中的某一分支失败时（如 `clang-format.sh` 失败降级到 `clang-format.ps1`），当前没有办法查看具体失败原因（错误被重定向到 `/dev/null`）。

### 4. `project-config.json` 的 `encoding` 字段默认值为空

`templates/harness/project-config.json` 第 4 行：
```json
"encoding": ""
```
但文档中说明设置 `"encoding": "gbk"` 可启用 GBK 支持。空值的行为是什么（默认 UTF-8？跳过编码转换？）未文档化。

---

*关注点审计：2026-06-14*
