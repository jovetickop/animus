# Pitfalls Research

**Domain:** 多语言代码审查编排框架 / Claude Code 技能插件 (harness-cc)
**Researched:** 2026-06-14
**Confidence:** HIGH (大部分发现已验证存在于当前代码库中)

## Critical Pitfalls

这些是会导致数据损坏、安全漏洞或重大重写的陷阱，必须在技术债务修复阶段优先处理。

---

### Pitfall 1: PowerShell 默认编码的隐蔽契约

**What goes wrong:**
PowerShell 5.1 的不同 cmdlet 对不同操作使用不同默认编码，且 Google 流行的意见中有大约一半是错误的。最常见的坑：`Out-File` 和重定向操作符 `>` 默认输出 **UTF-16LE**（带 BOM），而 `Set-Content` 默认输出 **ANSI**（Windows-1252）。结果：同一个仓库内出现 3 种编码共存的混乱局面。

- `Out-File` / `>` -> UTF-16LE（Git 视作二进制文件，diff 显示每字节间填充 `\0`）
- `Set-Content` -> ANSI (Windows-1252)
- `New-ModuleManifest` -> UTF-16LE（PSGallery 模块清单的常见陷阱）
- PowerShell Core 6+ 改为 UTF-8 无 BOM，但 Windows 自带的是 5.1

**Why it happens:**
PowerShell 团队为向后兼容选择了保守的默认编码。`>` 不是重定向操作的独立实现，而是 `Out-File` 的别名。Google 搜索"PowerShell write file encoding"的结果中充斥着过时或错误的建议。开发者直到 `git diff` 输出乱码时才意识到问题。

**本项目现状：**
当前仓库有 **7 个 UTF-16LE .ps1 文件**（`templates/harness/` 和 `commands/` 目录），同一仓库内还有 UTF-8 编码的 `hooks/scripts/` 文件。Git diff 无法正确显示 UTF-16LE 文件的变更，中文注释在历史提交中已损坏（commit `628f02c` 证实）。

**How to avoid:**
1. 在仓库中强制执行编码策略文档，声明"所有脚本必须使用 UTF-8 with BOM"
2. 所有 PowerShell 脚本中显式指定编码：`-Encoding UTF8` 或 `-Encoding utf8BOM`
3. 禁止裸 `>` 重定向操作；强制使用 `| Out-File -Encoding utf8` 或 `| Set-Content -Encoding utf8`
4. `.editorconfig` 中声明 `charset = utf-8`
5. 在 CI 中添加编码检测步骤：`git grep -Il $'\xFE\xFF'` 检测 UTF-16LE BOM

**Warning signs:**
- `git diff` 显示 `\0` 字节或"binary files differ"而非文本差异
- 文件在 VS Code 中显示为 UTF-16 LE
- 文件大小异常（UTF-16LE 是 UTF-8 的 2 倍）
- `file` 命令输出 "Little-endian UTF-16 Unicode" 而非 "UTF-8"

**Recovery (已经发生):**
```powershell
# 检测 UTF-16LE 文件
Get-ChildItem -Recurse *.ps1 | Where-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE
}

# 转换 UTF-16LE -> UTF-8 with BOM
Get-Content -Path file.ps1 | Set-Content -Encoding UTF8 -Path file.ps1

# Git 重新规范化
git add --renormalize .
```

**Phase to address:**
Phase 1 (TECHD-01, TECHD-03) — 编码统一必须先于所有其他变更，因为编码转换会影响 Git 历史、影响后续所有 diff，且其他技术债务修复也在同一批文件中。

---

### Pitfall 2: Invoke-Expression 作为默认命令执行方式

**What goes wrong:**
`Invoke-Expression`（别名 `iex`）将任意字符串作为 PowerShell 代码求值。当字符串包含用户输入或来自配置文件的外部数据时，攻击者可以注入任意命令。Microsoft 官方将其列为"高危"并推荐"仅作为最后手段使用"。

```powershell
# 本项目的实际代码 (run-regression.ps1)
$buildCmd = $config.'build-command'
Invoke-Expression $buildCmd  # 如果 buildCmd 包含 ";恶意代码" 则会被执行
```

**Why it happens:**
`Invoke-Expression` 是"最容易想到"的动态命令执行方式。开发者看到"需要执行一个存储为字符串的命令"时，直觉反应就是 `iex`。PSScriptAnalyzer 的 `AvoidUsingInvokeExpression` 规则是后来才成为标准的。

**本项目现状：**
`templates/harness/run-regression.ps1` 第 16、24、40 行的构建命令、测试命令和运行命令均通过 `Invoke-Expression` 执行。这些命令来自 `project-config.json`，虽然是开发者自己配置的，但仍然是脚本注入的潜在入口。

**How to avoid:**
按照以下优先级选择替代方案：

| 场景 | 推荐替代 | 理由 |
|------|----------|------|
| 运行外部进程 | `Start-Process` + `-ArgumentList` | 参数被当作数据而非代码 |
| 命令名在变量中 | 调用运算符 `& $command` | 仅解析命令名，不解析参数中的特殊字符 |
| 需要参数分离 | Splatting `@Params` | 参数作为哈希表传递 |
| 必须构建完整命令 | `[ScriptBlock]::Create()` + `&` | 可配合 AST 检查约束语言模式 |
| 绝对不得已 | 受限运行空间 | 使用 `Start-Job` + 受限初始化脚本 |

```powershell
# 好: Start-Process (外部进程)
$buildCmd = $config.'build-command'
$parts = $buildCmd.Split(' ', 2)  # 拆分为程序和参数
Start-Process -FilePath $parts[0] -ArgumentList $parts[1] -Wait -NoNewWindow

# 更好: & 调用运算符 (PowerShell 命令)
$commandParts = $buildCmd.Split(' ', 2)
$cmdName = $commandParts[0]
$cmdArgs = @()
if ($commandParts.Length -gt 1) {
    # 安全分割参数
    $cmdArgs = @($commandParts[1])
}
& $cmdName @cmdArgs
```

**Warning signs:**
- PSScriptAnalyzer 报告 `AvoidUsingInvokeExpression` 警告
- 任何来自 JSON/YAML 配置的字符串直接被 `Invoke-Expression`
- `iex` 出现在代码审查的 diff 中

**Recovery (已经发生):**
替换 `run-regression.ps1` 中的 `Invoke-Expression` 为 `&` 调用运算符 + `Start-Process`。由于命令来自开发者控制的 JSON 配置，风险等级为"中"而非"高"，但替换是最佳实践。

**Phase to address:**
Phase 2 (TECHD-07) — 在编码统一之后执行，因为文件本身需要先转换为 UTF-8。

---

### Pitfall 3: 跨平台 Shell 脚本换行符污染

**What goes wrong:**
Shell 脚本（`.sh` 文件）在 Unix/Linux/macOS 上要求使用 LF 换行符。CRLF 换行符会导致 `#!/bin/bash` 行被解释为 `#!/bin/bash\r`，shell 报错 "No such file or directory"，脚本完全无法执行。

**Why it happens:**
Windows 上的编辑器（VS Code、Notepad++ 等）默认使用 CRLF。开发者在 Windows 上创建 Shell 脚本后，如果没有设置"保存为 LF"或没有 `.gitattributes` 自动转换，提交的脚本就是 CRLF。`core.autocrlf=true` 在旧版 Git 中可能不会转换 `.sh` 文件。

**本项目现状：**
`.claude/hooks/scripts/` 下的所有 `.sh` 文件（`pre-compact.sh`、`pre-tool-use.sh`、`stop-check.sh`）使用 CRLF 换行符，而 `templates/harness/update-progress.ps1` 混用 CRLF 和 LF。Shell 脚本在 WSL、macOS、Linux 上会直接失败。

**How to avoid:**
1. `.gitattributes` 中强制 `.sh` 使用 LF：
   ```gitattributes
   *.sh text eol=lf
   ```
2. `.editorconfig` 中按文件类型配置换行符：
   ```ini
   [*.sh]
   end_of_line = lf
   ```
3. CI 中检测 CRLF 在 `.sh` 文件中：
   ```bash
   # 检测 .sh 文件中是否包含 CR
   grep -rl $'\r$' --include='*.sh' . && exit 1
   ```
4. 使用 `git add --renormalize .` 修复已跟踪文件

**Warning signs:**
- Shell 脚本执行时报 "No such file or directory" 但文件确实存在
- `cat -v script.sh` 显示行尾 `^M`
- `file script.sh` 输出 "CRLF line terminators"
- `git ls-files --eol` 显示 `.sh` 文件为 `crlf`

**Recovery (已经发生):**
```bash
# 修复所有 .sh 文件换行符
find . -name '*.sh' -exec sed -i 's/\r$//' {} \;

# 或使用 dos2unix
find . -name '*.sh' -exec dos2unix {} \;

# 添加 .gitattributes 后重新规范化
git add --renormalize .
```

**Phase to address:**
Phase 1 (TECHD-02) — 与编码统一同期执行，都是基础设施级别的修复。

---

### Pitfall 4: 正则解析 JSON 的脆弱性

**What goes wrong:**
使用正则表达式从 JSON 字符串中提取字段值，而不是使用 JSON 解析器。当 JSON 结构变化（字段顺序、转义字符、嵌套结构、包含冒号的字符串值）时，正则表达式会静默失败或返回错误值。

```powershell
# 本项目的实际代码 (clang-format.ps1, pre-tool-use.ps1)
$inputJson = $input | Out-String
if ($inputJson -notmatch '"file_path"\s*:\s*"([^"]+)"') { exit 0 }
```

这条正则无法处理：
- `file_path` 包含转义引号：`"file_path": "C:\\path\\with\\\"quotes\""`
- `file_path` 在字符串中间：`"file_path": "", "other": "value"`
- `file_path` 值包含冒号或空格：已经在 Windows 路径中常见
- JSON 格式化后 `file_path` 和 `:` 之间有多余空格或换行

**Why it happens:**
开发者认为"只是取一个字段，写正则比解析 JSON 更轻量"。实时上 PowerShell 5.1 的 `ConvertFrom-Json` 完全可用，且写正则的时间往往比调 API 更长。Claude Code hooks 的 stdin 输入格式是已知且稳定的 JSON 结构，但正则解析仍然脆弱。

**本项目现状：**
`clang-format.ps1`（第 5-6 行）、`pre-tool-use.ps1`（第 5-6 行）以及对应的 `.sh` 版本（使用 `sed` 解析 JSON）都使用正则而非 JSON 解析器。当节点字段顺序变化时，这些钩子静默失败。

**How to avoid:**
始终使用 JSON 解析器：

```powershell
# PowerShell 5.1+
try {
    $inputObj = $input | Out-String | ConvertFrom-Json
    $filePath = $inputObj.tool_input.file_path
    if (-not $filePath) { exit 0 }
} catch {
    Write-Error "JSON parse failed: $_" | Out-Null
    exit 1
}
```

```bash
# Shell 中使用 jq（需确保 jq 可用）
input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
[[ -n "$file_path" ]] || exit 0
```

如果必须兼容没有 `jq` 的环境，使用 Python 作为降级：
```bash
file_path=$(python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
```

**Warning signs:**
- Hook 脚本使用 `-notmatch`、`-match` 或 `sed` 解析 JSON
- Code review 中发现 JSON 字段被逐字符提取
- 测试 JSON 输入中包含转义字符或嵌套结构时失败

**Recovery (已经发生):**
逐个替换 `hooks/scripts/` 和 `.sh` 文件中的正则解析逻辑。注意保持"失败不阻塞"语义：JSON 解析失败应以 `exit 1`（非阻塞）而非 `exit 2`（阻塞）退出。

**Phase to address:**
Phase 2 (TECHD-08) — 与安全重构同期，需要编码统一完成后的可编辑文件。

---

### Pitfall 5: Hooks 双平台降级的调试真空

**What goes wrong:**
Claude Code hooks.json 中配置的 bash || PowerShell 双路径降级将错误输出吞噬到 `/dev/null`，导致任何分支的失败都静默无声，开发者无法排查问题。

```json
{
  "command": "bash \".../clang-format.sh\" 2>/dev/null || powershell .../clang-format.ps1 2>/dev/null || exit 0"
}
```

**后果链：**
1. Shell 脚本因 CRLF 换行符失败 -> stderr 被 `/dev/null` 吞噬
2. 降级到 PowerShell -> PowerShell 脚本也因某种原因失败 -> 再度被吞噬
3. `|| exit 0` 成功返回 -> Claude Code 认为一切正常
4. 格式化未执行 -> 代码提交后格式不一致 -> 下次格式化触发全量 diff

**Why it happens:**
`||` 短路逻辑的设计意图是"失败不阻塞"，但误用了 `2>/dev/null` 吞噬错误。设计者认为"用户不需要看到格式化工具的告警"，实际上却连致命错误也隐藏了。`timeout` 限制进一步压缩了调试窗口。

**本项目现状：**
所有 4 个钩子（clang-format、pre-tool-use、pre-compact、stop-check）都使用 `2>/dev/null` 模式。DOC 缺口同时存在：没有文档说明如何启用调试输出。

**How to avoid:**
1. 使用环境变量控制错误可见性：
   ```json
   {
     "command": "DEBUG=1 bash \".../script.sh\" 2>&1 || powershell \".../script.ps1\" 2>&1 || exit 0"
   }
   ```
   （注意：这会将错误暴露给用户，不适合生产环境）

2. 更好的方案：日志文件 + 条件输出：
   ```json
   {
     "command": "bash \".../script.sh\" >> \"$CLAUDE_PROJECT_DIR/.claude/hooks/hooks.log\" 2>&1 || powershell \".../script.ps1\" >> \"$CLAUDE_PROJECT_DIR/.claude/hooks/hooks.log\" 2>&1 || exit 0"
   }
   ```

3. 在文档中说明调试方法：
   ```bash
   # 手动运行以查看错误
   powershell -NoProfile -File .claude/hooks/scripts/clang-format.ps1 < test_input.json
   ```

**Warning signs:**
- `hooks.json` 中使用 `2>/dev/null` 或 `2>$null`
- 格式化工具停止工作但没有任何错误提示
- `.sh` 脚本因 CRLF 无法运行但 Claude 未报错

**Recovery (已经发生):**
1. 添加可选调试模式：通过环境变量 `HARNESS_DEBUG=1` 启用 stderr 输出
2. 为每个钩子添加日志文件写入
3. 在文档中补充调试章节（TECHD-11）

**Phase to address:**
Phase 2 (TECHD-11 文档补充) + Phase 3（作为 hooks 重构的一部分）

---

### Pitfall 6: Claude Code Hooks 的事件/类型注册错误

**What goes wrong:**
Claude Code hooks 有严格的事件类型和事件名称枚举，使用不存在的值会导致钩子静默失效。已知陷阱包括：

1. **无效事件类型**：使用 `"type": "log"` 或 `"type": "notification"` 而不是 `"type": "command"` / `"type": "prompt"` / `"type": "agent"`
2. **无效事件名称**：使用 `Setup`（不存在的旧事件名）而不是 `SessionStart`
3. **空 matcher 匹配 Agent 工具**：PostToolUse 钩子用 `"matcher": ""` 会匹配所有工具，包括 Agent 工具，导致 `$CLAUDE_TOOL_INPUT_FILE_PATH` 等变量不存在的错误
4. **插件中声明钩子但未在 settings.json 注册**：Claude Code 不从 `hooks/hooks.json` 自动读取插件钩子——必须在 `.claude/settings.json` 或 `~/.claude/settings.json` 中引用。
5. **`UserPromptSubmit` 在插件中注册但不执行**：已知 bug，此钩子类型的插件声明被匹配但命令始终不触发

**Why it happens:**
Claude Code 的钩子系统文档迭代较快，网上的示例代码容易过时。VSCode 扩展开发背景的开发者常把"插件自动注册钩子"的模式代入 Claude Code，但 Claude Code 需要显式声明。

**本项目现状：**
当前 hooks.json 使用的是有效的 `PreToolUse`、`PostToolUse`、`PreCompact`、`Stop` 事件和 `"type": "command"` 类型。但存在两个风险：
- 跨平台降级脚本（`.sh` + `.ps1`）同时注册在同一条命令中，`timeout` 配置覆盖了两个版本的执行时间
- 如果未来添加 `agent` 类型钩子，需要理解 `matcher` 的 case-sensitive 特性

**How to avoid:**
1. 始终从[官方 hooks 文档](https://code.claude.com/docs/en/hooks)引用有效事件列表
2. 保持 `matcher` 具体，避免空匹配或过于宽泛的正则
3. 插件钩子必须在 `settings.json` 中注册，仅在 `hooks/hooks.json` 声明是不够的
4. 使用 `timeout` 限制防止钩子阻塞（默认 60s 对格式化操作可能不够，建议 15-30s）

**Warning signs:**
- 钩子从未触发（查看 Claude Code 日志确认）
- 新事件添加后无效果
- matcher 正则过于简单（如 `".*"`）导致意外工具被匹配

**Phase to address:**
Phase 3 — 作为 hooks 重构时验证合规性

---

## Moderate Pitfalls

### Pitfall 7: 单脚本多职责膨胀

**What goes wrong:**
一个脚本承担 5 种以上不相关的职责，达到 400+ 行。修改一个功能时可能影响其他不相关功能，测试困难，新维护者难以理解全貌。

**本项目现状：**
`update-progress.ps1`（424 行）同时承担：参数验证、目标查找、状态转换校验（5 种状态的完整转换矩阵）、Oracle 验证、Markdown 报告生成、进度日志更新、Git 自动提交。违反了单一职责原则。

**How to avoid:**
按职责拆分：
- `validate-transition.ps1` — 状态转换合法性校验
- `oracle-runner.ps1` — 构建/测试命令执行
- `report-generator.ps1` — Markdown 报告 + 进度日志
- `git-committer.ps1` — Git 自动提交

**Split 策略：**
- 内部函数如果只被一个使用者调用 -> 留在原地
- 跨多个脚本共享的工具函数 -> 提取为 `.psm1` 模块
- 有独立配置或状态 -> 提取为独立脚本

**Phase to address:**
Phase 3 (TECHD-06) — 在编码统一和安全修复之后，因为涉及大量代码迁移。

---

### Pitfall 8: Dot-Sourcing 的副作用泄漏

**What goes wrong:**
使用 `. .\script.ps1` 将另一个脚本的变量和函数加载到当前作用域。这导致命名空间污染、变量意外覆盖、难以调试的 "为什么这个变量有值" 问题。

```powershell
# 潜在问题：.ps1 中的 $config 覆盖了调用者的 $config
. .\shared.ps1
# shared.ps1 中定义了 $config，覆盖了主脚本中的 $config
```

**与本项目的关系：**
虽然当前脚本没有过度使用 dot-sourcing（主要使用 `-NoProfile` 独立执行），但模块化拆分后（TECHD-06）如果不注意作用域隔离，可能引入此问题。拆分为 `.psm1` 模块而非 `.ps1` 文件可以避免。

**How to avoid:**
1. 将共享函数提取为 `.psm1` 模块（推荐）
2. 函数内部使用 `$script:` 前缀声明模块级变量
3. 使用 `[CmdletBinding()]` 确保参数隔离
4. 避免在函数外定义变量（全局作用域外的变量泄漏）

**Phase to address:**
Phase 3 — 在拆分 `update-progress.ps1` 时注意模块化设计。

---

### Pitfall 9: Python 2/3 跨版本兼容的 IO 陷阱

**What goes wrong:**
要求同时兼容 Python 2.7+ 和 Python 3.x 的脚本在某些 IO 操作上行为不同：

| 操作 | Python 2 | Python 3 | 注意 |
|------|----------|----------|------|
| `open()` 默认模式 | 二进制（不区分文本/二进制） | 文本模式 + 系统编码 | Python 3 中文本模式可能引发 `UnicodeDecodeError` |
| `print()` | 语句 | 函数 | 需要 `from __future__ import print_function` |
| `subprocess` 输出 | `str`（字节串） | `bytes`（需 `.decode()`） | 跨版本兼容需统一处理 |
| `json.load()` 输入 | 接受 `str` 或 `bytes` | 仅接受 `str` | 需确保读取时指定编码 |
| `sys.stdin.encoding` | 可能为 `None` | 通常有值 | 需回退到 `utf-8` |
| 除号 `/` | 整数除法 | 浮点除法 | 需要 `from __future__ import division` |

**本项目现状：**
所有 `.py` 脚本（`show-status.py`、`format-all.py`、`session-catchup.py`）要求 Python 2.7+/3.x 双兼容。`format-all.py` 使用 `subprocess.Popen` 调用外部格式化工具，返回值在不同 Python 版本中类型不同。

**How to avoid:**
```python
from __future__ import print_function, division, unicode_literals
import sys
import subprocess
import json

# 跨版本编码安全读取
def read_file(path):
    with open(path, 'rb') as f:
        data = f.read()
    # Python 2/3 兼容的 JSON 加载
    return json.loads(data.decode('utf-8'))

# 跨版本 subprocess 处理
def run_cmd(cmd):
    if sys.version_info[0] == 2:
        # Python 2: subprocess 返回 str
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        return proc.returncode, out, err
    else:
        # Python 3: 需要 text=True 或手动解码
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate()
        return proc.returncode, out, err
```

**Phase to address:**
Phase 3 — 作为审计技术债务时的代码审查标准。

---

### Pitfall 10: 格式化工具的"空转"与缓存缺失

**What goes wrong:**
格式化脚本执行了无意义的操作或重复 I/O，不必要地增加每次写入的延迟。

常见模式：
1. `cargo fmt --check`（只检查）然后立即 `cargo fmt`（真正格式化），--check 的输出被完全忽略
2. 每次文件写入都从头查找 `Cargo.toml` 目录（而不是缓存结果）
3. 格式化工具有错误时静默吞异常（`except Exception: return False`）

**本项目现状：**
`format-all.py` 的 `format_rust` 函数先执行 `cargo fmt --check`（浪费 I/O），忽略其退出码，再执行 `cargo fmt`。`Cargo.toml` 的目录查找每次重做（每个 Rust 文件写入触发一次全目录遍历）。

**How to avoid:**
```python
# 缓存 Cargo.toml 目录
_cargo_toml_cache = {}

def find_cargo_root(file_path):
    """缓存 Rust 项目根目录查找结果"""
    dir_path = os.path.dirname(file_path)
    if dir_path not in _cargo_toml_cache:
        current = dir_path
        while current and current != os.path.dirname(current):
            if os.path.exists(os.path.join(current, 'Cargo.toml')):
                _cargo_toml_cache[dir_path] = current
                break
            current = os.path.dirname(current)
        else:
            _cargo_toml_cache[dir_path] = None
    return _cargo_toml_cache[dir_path]

def format_rust(file_path):
    """格式化 Rust 文件"""
    root = find_cargo_root(file_path)
    if root:
        # 只执行一次 cargo fmt，不要先 --check
        subprocess.run(['cargo', 'fmt'], cwd=root,
                      capture_output=True, timeout=30)
```

**Warning signs:**
- `cargo fmt --check` 出现在日志中但其退出码被忽略
- 格式化的子进程调用在短时间内对同一目录重复执行
- `except Exception: pass` 或 `return False` 吞噬错误

**Phase to address:**
Phase 2 (TECHD-09) — 可以在编码统一后快速修复。

---

### Pitfall 11: 状态文件路径的双重查找分裂

**What goes wrong:**
同时支持新旧两个路径的状态文件查找逻辑，导致维护负担加倍，备份只覆盖一个路径时数据不一致。

**本项目现状：**
7 个脚本同时支持 `.claude/harness/features.json` 和 `.claude/state/features.json` 两个路径，且每个脚本的查找逻辑各有不同（共 6 种变体）。部分查找 `features.json`，部分查找 `project-config.json`，部分用 `$PSScriptRoot`，部分用 `cd` 遍历。

**How to avoid:**
1. 确定标准路径：`.claude/state/features.json`
2. 提取公共路径查找函数到一个位置（例如 `find-state.ps1` 或模块内）
3. 所有脚本调用统一函数
4. 旧路径文件保留一段过渡期，但日志记录"已弃用"警告

**Warning signs:**
- 同一个文件路径在代码库中硬编码多次
- 查找逻辑出现 3 种以上变体
- 新脚本需要重复实现相同的"向上遍历"逻辑

**Phase to address:**
Phase 2 (TECHD-04) — 在编码统一后，路径查找的前提是文件可读。

---

### Pitfall 12: 硬编码的用户路径

**What goes wrong:**
脚本中硬编码 `$env:USERPROFILE\.claude\skills\harness-cc` 路径，假设所有用户都安装在默认位置。当用户使用团队共享目录、多用户环境、便携式安装或自定义安装路径时，脚本无法定位技能源文件。

**How to avoid:**
优先使用环境变量或运行时检测：
```powershell
# 方案 1: 通过 SKILL.md 所在目录推断（推荐）
$SkillRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# 方案 2: 环境变量覆盖
$InstallRoot = $env:HARNESS_CC_ROOT
if (-not $InstallRoot) {
    $InstallRoot = Join-Path $env:USERPROFILE ".claude\skills\harness-cc"
}

# 方案 3: CLAUDE_PLUGIN_ROOT（Claude Code 提供的标准变量）
$SkillRoot = $env:CLAUDE_PLUGIN_ROOT
```

**Phase to address:**
Phase 3 (TECHD-10) — 非阻塞但影响首次配置体验。

---

## Minor Pitfalls

### Pitfall 13: Git 属性配置不完整

**What goes wrong:**
缺少 `.gitattributes` 导致 Git 对文件类型和编码的自动检测不一致。不同开发者的 `core.autocrlf` 配置不同，导致换行符在提交间反复转换。

**当前状态：**
仓库没有 `.gitattributes` 文件。这是换行符不一致（Pitfall 3）和编码混用（Pitfall 1）的系统性原因之一。

**推荐配置：**
```gitattributes
# 自动检测文本文件，统一为 LF
* text=auto

# Shell 脚本 - 必须 LF
*.sh text eol=lf
*.bash text eol=lf

# PowerShell 脚本 - CRLF（Windows 标准）
*.ps1 text eol=crlf
*.psd1 text eol=crlf
*.psm1 text eol=crlf
*.bat text eol=crlf
*.cmd text eol=crlf

# 跨平台源文件 - LF
*.py text eol=lf
*.json text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.md text eol=lf
*.txt text eol=lf

# 二进制文件 - 不转换
*.png binary
*.jpg binary
*.pdf binary
*.exe binary
*.dll binary
*.ico binary
```

### Pitfall 14: 缺少 .editorconfig

**What goes wrong:**
没有 `.editorconfig` 文件，不同编辑器对新文件的默认设置不同。VS Code 默认 CRLF + UTF-8，Linux 编辑器默认 LF + UTF-8。

**推荐配置：**
```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.ps1]
end_of_line = crlf

[*.{sh,bash}]
end_of_line = lf

[*.md]
trim_trailing_whitespace = false
```

### Pitfall 15: JSON 模板角色不明确

**What goes wrong:**
同名或类似文件放在不同目录，且用途无文档说明。新维护者不敢删除任何文件，导致文件膨胀。

**当前状态：**
`templates/state/` 下有三个 JSON 文件，格式各不相同。它们与 `templates/harness/features.json`（由 `init-project.ps1` 复制到目标项目）的关系不明确。`features.json` 本身在仓库中有 3 个版本。

**修复方法：**
1. 删除或合并多余版本
2. 创建 `TEMPLATE-ROLES.md` 说明每个模板的用途和安装目标
3. 确保 `init-project.ps1` 只从一个位置获取默认配置

**Phase to address:**
Phase 1 (TECHD-05) — 编码统一前可以快速完成，但最好在路径统一（TECHD-04）后一起做。

---

## Technical Debt Patterns

| 短路做法 Shortcut | 即时收益 Immediate Benefit | 长期代价 Long-term Cost | 何时可以接受 When Acceptable |
|---|---|---|---|
| `Invoke-Expression` 运行配置命令 | 一行代码实现动态执行 | 命令注入风险、参数引用错误、PSScriptAnalyzer 警告 | 从不，总有安全的替代方案 |
| 正则解析 JSON | 避免依赖 JSON 解析器 | 结构变化静默失败、转义处理缺失 | 仅用于一次性的 ad-hoc 脚本 |
| UTF-16LE 编码 .ps1 | 无需手动指定编码（Windows 自带） | Git 二进制文件、diff 不可读、中文乱码 | 从不，统一使用 UTF-8 with BOM |
| .sh 使用 CRLF | 编辑后不需要换行符转换 | Linux/macOS 上直接报错 | 从不 |
| 单脚本 400+ 行 | 减少文件数量、"都在一处" | 职责混杂、测试困难、合并冲突 | 脚本少于 100 行且生命周期短 |
| 硬编码 `$env:USERPROFILE` | 简单直接，立即生效 | 便携性丧失、多用户环境失败 | 仅用于个人快速脚本 |
| `2>/dev/null` 吞噬所有错误 | 用户界面"干净" | 调试无门、静默失败难以发现 | 有条件：配合日志文件或 DEBUG 模式 |
| 双重路径支持旧版 | 向后兼容 | 每个新功能需实现两次、路径逻辑增加 6 种变体 | 仅过渡期（最多 1 个版本） |

---

## Integration Gotchas

| 集成点 | 常见错误 | 正确做法 |
|--------|----------|----------|
| Claude Code PreToolUse | 没有处理 `updatedInput` 被 Agent 工具静默忽略的 bug（已知 #39814） | 使用 `SubagentStart` 的 `hookSpecificOutput` 注入额外上下文 |
| Claude Code PostToolUse | 空 `matcher` 匹配 Agent 工具导致脚本错误 | 明确的 matcher：`"matcher": "Write|Edit|Bash|Read"` |
| Claude Code Plugin hooks | 在插件 `hooks/hooks.json` 声明但未在 `settings.json` 注册 | 始终在 `.claude/settings.json` 或 `~/.claude/settings.json` 引用 |
| Git `working-tree-encoding` | 配置 UTF-16 后未 `git add --renormalize`，导致空字节污染 | 修改 `.gitattributes` 后立即 `git add --renormalize .` |
| Python JSON 解析 | Python 2 中 `json.load` 接受 `bytes`，Python 3 不接受 | 始终解码为 `str` 再传入 `json.loads` |
| PowerShell 管道 | `Out-String` 不带 `-Width` 参数时截断长行（默认 80 字符） | `Out-String -Width 4096` 或使用 `-Raw` 参数 |

---

## Performance Traps

| 陷阱 | 症状 | 防止方法 | 何时爆发 |
|------|------|----------|----------|
| `cargo fmt --check` + `cargo fmt` 双重执行 | 每个 Rust 文件写入触发 2 次 `cargo fmt` | 移除 `--check` 调用，只执行一次 | 始终存在（每个写入操作） |
| `Cargo.toml` 目录查找不缓存 | N 个 Rust 文件写入触发 N 次目录遍历 | 使用 `functools.lru_cache` 或手动缓存 | 3+ Rust 文件/会话 |
| PS hook 脚本每次启动 Python 解释器 | `python format-all.py` 启动开销 ~100ms | 使用服务器模式或仅 Python 环境时跳过 | 每次 ToolUse（频率最高） |
| 大 JSON 文件用正则解析 | 匹配失败但无错误提示 | 使用 `ConvertFrom-Json` | 任意非简单 JSON |
| PowerShell `Out-String` 默认宽度 | 长行在管道中被截断 | `Out-String -Width 4096` | 文件路径超过 80 字符时 |
| `Get-Content` 不带 `-Raw` | 大文件逐行读取导致多次 `ConvertFrom-Json` 调用 | `-Raw` 参数一次性读取 | 1MB+ 的 JSON 文件 |

---

## Security Mistakes

| 错误 | 风险 | 防范 |
|------|------|------|
| `Invoke-Expression` 执行配置命令 | 命令注入，JSON 配置中的恶意命令直接执行 | 使用 `Start-Process` + `-ArgumentList` 或 `&` 调用运算符 |
| `.mcp.json` 模板中的 API 密钥变量被提交 | 凭证泄露到公开仓库 | 文档强调 `.mcp.json` 加入 `.gitignore`，模板中使用占位符 |
| Hook 脚本输出文件路径到控制台 | 间接信息泄露（文件结构暴露） | 仅在 DEBUG 模式下输出路径 |
| 硬编码用户路径 | 权限提升或路径遍历 | 使用环境变量 + 运行时检测 |
| JSON 配置中空命令字段 | 未定义行为（空字符串被当作命令执行） | 空字段跳过执行并提示用户配置 |

---

## "Looks Done But Isn't" Checklist

评审技术债务修复时逐项检查：

- [ ] **编码统一 (TECHD-01):** 7 个 UTF-16LE 文件全部转换且 `file` 命令确认。容易漏掉 `commands/` 目录下的文件
- [ ] **换行符修复 (TECHD-02):** `.sh` 文件 `grep -rl $'\r$'` 返回空。容易漏掉勾子脚本和模板目录下的
- [ ] **中文注释恢复 (TECHD-03):** 乱码恢复后检查 `update-progress.ps1` 的中文状态摘要。容易漏掉隐式字符串（非注释）
- [ ] **Invoke-Expression 替换 (TECHD-07):** `git grep 'Invoke-Expression'` 和 `git grep '\biex\b'` 都返回空。注意区分大小写和别名用法
- [ ] **正则解析替换 (TECHD-08):** `.ps1` 和 `.sh` 文件中所有 JSON 提取都使用了解析器。注意检查 `.sh` 文件的 `sed` 用法
- [ ] **路径统一 (TECHD-04):** `git grep '\.claude/harness/features\.json'` 除了注释外不再出现
- [ ] **双重 cargo fmt (TECHD-09):** `git grep 'cargo fmt --check'` 返回空
- [ ] **`.gitattributes` 配置:** 文件存在且 `git ls-files --eol` 显示所有 `.sh` 为 `lf`，`.ps1` 为 `crlf`

---

## Recovery Strategies

| 问题 | 恢复成本 | 恢复步骤 |
|------|----------|----------|
| UTF-16LE 文件编码混乱 | 中 | 1) 批量转换：`Get-Content` + `Set-Content -Encoding UTF8` 2) `git add --renormalize .` 3) 验证 diff 可读 |
| .sh 文件换行符 CRLF | 低 | 1) `find . -name '*.sh' -exec sed -i 's/\r$//' {} \;` 2) 添加 `.gitattributes` |
| 中文注释已损坏（二进制乱码） | 中-高 | 1) 编码转换后检查乱码位置 2) 对照英文注释重新翻译 3) 或从 Git 历史提取未损坏版本 |
| `Invoke-Expression` 安全漏洞 | 低 | 1) 替换为 `Start-Process` 或 `&` 2) PSScriptAnalyzer 验证无警告 |
| 状态文件路径双重查找 | 中 | 1) 确定标准路径 2) 提取查找函数 3) 逐个替换 7 个脚本 4) 旧路径加 `-WarningAction` |
| "已完成但不完整"的格式化 | 低 | 1) 修复 `cargo fmt` 双重执行 2) 添加缓存 3) 添加异常日志 |
| 硬编码路径导致安装失败 | 低 | 1) 替换为 `$PSScriptRoot` 相对路径或环境变量 2) 测试自定义路径场景 |

---

## Pitfall-to-Phase Mapping

| Pitfall | 预防阶段 | 验证方法 |
|---------|----------|----------|
| UTF-16LE 编码陷阱 | Phase 1 (TECHD-01, -03) | `file *.ps1` 确认统一为 UTF-8；`git diff` 确认可读 |
| 跨平台换行符污染 | Phase 1 (TECHD-02) | `grep -rl $'\r$' *.sh` 为空；`.gitattributes` 已配置 |
| JSON 模板角色不明确 | Phase 1 (TECHD-05) | 模板目录只有必要的文件，角色文档存在 |
| Invoke-Expression 注入 | Phase 2 (TECHD-07) | PSScriptAnalyzer `AvoidUsingInvokeExpression` 无警告 |
| 正则解析 JSON 脆弱性 | Phase 2 (TECHD-08) | 所有 `.ps1`/`.sh` 使用 `ConvertFrom-Json`/`jq` |
| 状态文件路径分裂 | Phase 2 (TECHD-04) | `git grep` 旧路径仅出现在注释中 |
| 格式化空转/缓存缺失 | Phase 2 (TECHD-09) | 观察 hooks 日志确认单次 `cargo fmt` |
| 单脚本多职责膨胀 | Phase 3 (TECHD-06) | 每个拆分后的文件职责单一，<150行 |
| 硬编码路径 | Phase 3 (TECHD-10) | 所有路径使用相对或环境变量方式 |
| Hooks 调试真空 | Phase 3 (TECHD-11) | 存在调试文档，DEBUG 模式可用 |
| Dot-sourcing 副作用 | Phase 3 (隐式) | 拆分脚本使用 `.psm1` 模块而非 `.ps1` |
| Git 属性配置不完整 | Phase 1 (新增) | `.gitattributes` 文件存在且覆盖所有文件类型 |
| `.editorconfig` 缺失 | Phase 1 (新增) | `.editorconfig` 文件存在 |

---

## Sources

- [Microsoft: Avoid using Invoke-Expression](https://learn.microsoft.com/en-us/powershell/scripting/learn/deep-dives/avoid-using-invoke-expression) — 官方警示，HIGH 可信度
- [PowerShell Team Blog: Invoke-Expression considered harmful](https://devblogs.microsoft.com/powershell/invoke-expression-considered-harmful/) — 团队博客，HIGH 可信度
- [PSScriptAnalyzer: AvoidUsingInvokeExpression](https://github.com/PowerShell/PSScriptAnalyzer/blob/master/RuleDocumentation/AvoidUsingInvokeExpression.md) — 官方规则文档，HIGH 可信度
- [SFEIR Institute: Custom commands and skills - Common mistakes](https://institute.sfeir.com/en/claude-code/claude-code-custom-commands-and-skills/errors/) — Claude Code 技能开发的最常见错误排名，HIGH 可信度
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) — 官方 hooks 文档，HIGH 可信度
- [GitHub: git-for-windows working-tree-encoding bug #5078](https://github.com/git-for-windows/git/issues/5078) — UTF-16 编码在 Git 中的 BUG 报告，HIGH 可信度
- [GitHub: PowerShell New-ModuleManifest UTF-16 issue #3789](https://github.com/PowerShell/PowerShell/issues/3789) — 已知 PowerShell 模块清单编码问题，HIGH
- [Microsoft Docs: ConvertFrom-Json (PowerShell 5.1)](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/convertfrom-json?view=powershell-5.1) — 官方 API 参考，HIGH
- [PowerShell: Preventing script injection attacks](https://learn.microsoft.com/en-us/powershell/scripting/security/preventing-script-injection) — 脚本注入防御指南，HIGH
- [GitHub: Claude Code PreToolUse updatedInput bug #39814](https://github.com/anthropics/claude-code/issues/39814) — 已知 hooks 问题，MEDIUM（取决于修复进度）
- [GitHub: VS Code UTF-16 encoding corruption via Out-File](https://github.com/microsoft/vscode/issues/291968) — AI agent 编辑 UTF-16 文件的编码循环问题，MEDIUM
- [GitHub Docs: Configuring Git to handle line endings](https://docs.github.com/en/get-started/git-basics/configuring-git-to-handle-line-endings) — 官方换行符配置指南，HIGH
- [Mike F. Robbins: PowerShell Script Module Design Philosophy](https://mikefrobbins.com/2018/09/21/powershell-script-module-design-philosophy/) — 模块化 PowerShell 最佳实践，HIGH
- [GitHub: orchestrator bypasses start-task hooks #315](https://github.com/Jamie-BitFlight/claude_skills/issues/315) — 已知 inline 执行绕过 hooks 的问题，MEDIUM
- [Stack Overflow: Git diff thinks line endings are LF when EOL is set to CRLF](https://stackoverflow.com/posts/40541706/revisions) — gitattributes 换行符行为澄清，MEDIUM
- [CSDN: Windows 11 23H2 BOM 处理逻辑改写](https://wenku.csdn.net/column/aotprw67xuo7) — Windows 11 编码契约变更，MEDIUM（内容质量需交叉验证）

---

## 对本项目技术债务修复的特别提示

当前代码库的陷阱叠加效应：多个陷阱同时作用于同一文件。例如 `update-progress.ps1` 同时具有 **UTF-16LE 编码（Pitfall 1）**、**单脚本多职责（Pitfall 7）**、**中文注释损坏（Pitfall 1 后果）**、**CRLF/LF 混用（Pitfall 3）**。修复顺序很重要：

1. **先编码统一**（Phase 1）—— 任何其他修改前，先把文件转为 UTF-8 with BOM，否则 Git diff 无法正确显示变更
2. **再替换不安全/脆弱代码**（Phase 2）—— `Invoke-Expression` → `&`；正则解析 → `ConvertFrom-Json`；路径统一
3. **最后模块化**（Phase 3）—— 在文件可读、代码安全的基础上拆分职责

不能在 "修复编码" 和 "修复代码" 之间反复切换——每次编码转换都会使之前修改的 diff 变得无法阅读。

*Pitfalls research for: ty-qt-ai-plugin / harness-cc*
*Researched: 2026-06-14*
