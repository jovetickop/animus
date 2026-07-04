# 写代码门控 PreToolUse Hook（Quick Dev 子文档）

> 所属任务：⑤ Quick Dev — 任务门控的硬拦截层
> 解决：agent 自觉不够可靠，需 hook 硬拦截无任务写代码
> 解决：agent 自觉不够可靠，需 hook 硬拦截无任务写代码

---

## 一、更改原因

### 1.1 当前问题

- `/animus-dev` 的 implementer 指令写了"只从 features.json 读任务"的规则
- 但 agent 可能忘记遵守这条规则，直接根据用户口述改代码
- 没有硬拦截机制，写代码前不检查是否有 in_progress 任务
- 结果是 features.json 里没有任务记录，代码却改了

### 1.2 解决后的效果

- 项目源码文件 Write/Edit 前自动检查 features.json 有无 in_progress 任务
- 没有任务 → 拒绝写入，提示先完成需求确认
- 白名单路径放行（状态文件、配置文件、文档）
- 双平台支持（bash + PowerShell），不阻塞正常操作

---

## 二、更改方案

### 2.1 实现位置

复用现有的 PreToolUse hook，匹配 `Write|Edit`：

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/write-gate.sh\" 2>/dev/null || powershell -ExecutionPolicy Bypass -File \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/write-gate.ps1\" 2>/dev/null || exit 0",
      "timeout": 5
    }
  ]
}
```

注意：与现有 PreToolUse（备份 + GBK 转换）**并存**，不替代。两个 hook 可以注册在同一 matcher 下。

### 2.2 门控逻辑

```python
def check_write_gate(file_path):
    # 1. 白名单检查
    if is_whitelisted(file_path):
        return ALLOW  # 放行

    # 2. 查找 features.json
    features_path = find_features_json(file_path)
    if not features_path:
        return ALLOW  # 没有 features.json = 未初始化 animus，放行

    # 3. 检查有无 in_progress 任务
    features = load_json(features_path)
    if has_in_progress_task(features):
        return ALLOW  # 有任务，放行

    # 4. 没有 in_progress 任务 → 拒绝
    return BLOCK
```

### 2.3 白名单规则

以下路径的 Write/Edit 放行，不检查任务：

| 模式 | 原因 |
|------|------|
| `.claude/animus/**` | 状态文件写入（features.json、memlog、handoff.json） |
| `.claude/**` | 配置文件（settings.json、plugin.json） |
| `**/*.md` | 文档（README、规范、报告） |
| `**/.gitignore` | git 配置 |
| `.editorconfig` | 编辑器配置 |

实现上通过路径前缀匹配：

```python
WHITELIST_PATTERNS = [
    ".claude/",
    ".claude-animus/",  # 兼容旧版路径
]

def is_whitelisted(file_path):
    normalized = file_path.replace("\\", "/")
    for pattern in WHITELIST_PATTERNS:
        if normalized.startswith(pattern) or normalized.endswith(".md"):
            return True
    return False
```

### 2.4 拦截后的行为

```bash
# Write 被拒绝时，hook 输出到 stderr：
echo "❌ 阻塞：写代码前需要先有 in_progress 任务" >&2
echo "   请先执行 /animus-dev 完成需求确认和任务拆分" >&2
exit 1
```

Claude Code 收到 exit 1 后会中断 Write 工具调用并向用户显示错误信息。

**注意：** 拒绝时 exit 1，而非 exit 0。exit 0 会让 Write 继续执行，等于没拦截。

### 2.5 bash 实现（write-gate.sh）

```bash
#!/bin/bash
# 写代码门控 — Write/Edit 前检查是否有 in_progress 任务
# exit 1 = 阻塞，exit 0 = 放行

input=$(cat)

# 解析操作类型和文件路径
operation=$(echo "$input" | jq -r '.tool // .name // empty' 2>/dev/null)
[ -z "$operation" ] && exit 0
case "$operation" in Write|Edit) ;; *) exit 0 ;; esac

file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$file_path" ] && exit 0
file_path="${file_path//\\//}"

# 白名单检查
case "$file_path" in
    .claude/*|.claude-animus/*) exit 0 ;;
    *.md) exit 0 ;;
esac

# 查找 features.json
dir=$(dirname "$file_path")
features_path=""
while [ -n "$dir" ] && [ -d "$dir" ]; do
    candidate="$dir/.claude/animus/features.json"
    if [ -f "$candidate" ]; then
        features_path="$candidate"
        break
    fi
    parent=$(dirname "$dir")
    [ "$parent" = "$dir" ] && break
    dir="$parent"
done

[ -z "$features_path" ] && exit 0

# 检查有无 in_progress 任务
in_progress=$(jq '[.tasks[] | select(.status == "in_progress")] | length' "$features_path" 2>/dev/null)
if [ "$in_progress" -gt 0 ] 2>/dev/null; then
    exit 0  # 有任务，放行
fi

# 无任务，阻塞
echo "❌ 阻塞：写代码前需要先有 in_progress 任务" >&2
echo "   请先执行 /animus-dev 完成需求确认和任务拆分" >&2
exit 1
```

### 2.6 PowerShell 实现（write-gate.ps1）

```powershell
# 写代码门控 — Write/Edit 前检查是否有 in_progress 任务
# exit 1 = 阻塞，exit 0 = 放行

try {
    $inputObj = $input | ConvertFrom-Json
} catch { exit 0 }

$operation = if ($inputObj.tool) { $inputObj.tool } else { $inputObj.name }
if (-not $operation) { exit 0 }
if ($operation -notmatch '^(Write|Edit)$') { exit 0 }

$filePath = $inputObj.tool_input.file_path
if (-not $filePath) { exit 0 }
$filePath = $filePath -replace '\\\\', '\'

# 白名单检查
if ($filePath -match '^\.claude[\\/]' -or $filePath -match '\.md$') { exit 0 }

# 查找 features.json
$dir = Split-Path $filePath -Parent
$featuresPath = $null
while ($dir -and (Test-Path $dir)) {
    $candidate = Join-Path $dir ".claude\animus\features.json"
    if (Test-Path $candidate) { $featuresPath = $candidate; break }
    $parent = Split-Path $dir -Parent
    if ($parent -eq $dir) { break }
    $dir = $parent
}
if (-not $featuresPath) { exit 0 }

# 检查有无 in_progress 任务
try {
    $features = Get-Content $featuresPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $inProgress = $features.tasks.PSObject.Properties | Where-Object { $_.Value.status -eq "in_progress" }
    if ($inProgress) { exit 0 }  # 有任务，放行
} catch { exit 0 }

# 无任务，阻塞
Write-Error "❌ 阻塞：写代码前需要先有 in_progress 任务"
Write-Error "   请先执行 /animus-dev 完成需求确认和任务拆分"
exit 1
```

### 2.7 改动文件

| 文件 | 改动 |
|------|------|
| 新建 `hooks/scripts/write-gate.sh` | bash 门控实现 |
| 新建 `hooks/scripts/write-gate.ps1` | PowerShell 门控实现 |
| 修改 `hooks/hooks.json` | PreToolUse 新增 write-gate hook |

### 2.8 配置绕过

通过 `config.toml` 控制门控开关，立即生效：

```toml
[gates]
require_task_before_write = true   # false = 关闭写门控
```

关闭后，所有 Write/Edit 操作不经检查直接放行。

### 2.9 注意事项

- **timeout: 5s** — 门控逻辑必须快，超时 exit 0 放行
- **双平台部署** — bash 优先，PowerShell 降级
- **失败安全** — 任何解析失败 exit 0（放行），绝不阻塞正常操作
- **hook 链顺序** — 门控 → 备份。门控 exit 1 阻塞时，备份也不会执行（正确行为，拦截后不需要备份）
- **脚本自身错误** — 內部解析错误或 JSON 读失败 → exit 0 放行（失败安全），只有确定无任务才 exit 1
- **与现有 PreToolUse 共存的顺序**：

```json
"PreToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [
      { "command": "...write-gate.sh...", "timeout": 5 },   # 门控先运行
      { "command": "...pre-tool-use.sh...", "timeout": 10 }  # 备份后运行
    ]
  }
]
```

门控先运行，拒绝后不执行备份。放行了才继续备份。

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 每次 Write/Edit 增加约 5ms（读 + 解析 features.json），超时 5s 兜底 |
| 兼容性 | 旧项目无 features.json 时自动放行，零破坏 |
| 降级 | 配置 `require_task_before_write = false` 完全关闭；脚本自身错误 exit 0 放行 |

## 四、验证方法

1. **无任务写代码**：确保 features.json 无 in_progress 任务 → Write 一个 .cpp 文件 → 确认被拒绝
2. **有任务写代码**：手动设置一个任务为 in_progress → Write 同文件 → 确认放行
3. **白名单写状态文件**：Write `.claude/animus/features.json` → 确认放行
4. **白名单写文档**：Write `README.md` → 确认放行
5. **无 features.json**：在未初始化项目 Write → 确认放行
6. **非 Write/Edit 操作**：Read、Glob 等 → 确认不触发
7. **超时安全**：模拟慢解析 → 确认 5s 后放行
