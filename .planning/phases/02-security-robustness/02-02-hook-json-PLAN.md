# 02-02: 修复 Hook 脚本 JSON 解析

**Plan ID:** 02-02
**Wave:** 1（与 02-01、02-03 并行）
**TECHD:** TECHD-08
**Autonomous:** true
**Files Modified:**
- .claude/hooks/scripts/clang-format.ps1
- .claude/hooks/scripts/pre-tool-use.ps1
- .claude/hooks/scripts/clang-format.sh
- .claude/hooks/scripts/pre-tool-use.sh

## Objective
将 4 个 Hook 脚本中脆弱的正则/sed 解析 JSON 方式替换为 `ConvertFrom-Json`（PS）或 `jq`/Python（Shell）。

## Research Summary
- PowerShell: 用 `$input | ConvertFrom-Json` 替代 `-notmatch` 正则
- Shell: 用 `jq` 或 Python `json.loads` 替代 `sed` 提取
- 保留 `exit 0` 失败不阻塞语义
- 修复转义字符、嵌套 JSON 等边缘情况

## Tasks

### Task 1: 修复 PowerShell Hook 脚本

**read_first:**
- .claude/hooks/scripts/clang-format.ps1
- .claude/hooks/scripts/pre-tool-use.ps1

**action:**
1. 读取两个 .ps1 文件
2. 找到使用 `Out-String + -notmatch` 提取 JSON 字段的代码段
3. 替换为：
   ```powershell
   try {
     $inputObj = $input | ConvertFrom-Json
     $filePath = $inputObj.tool_input.file_path
     if (-not $filePath) { exit 0 }
   } catch {
     exit 0
   }
   ```
4. 保留所有后续逻辑（encoding bridge, clang-format 调用等）

**acceptance_criteria:**
- `grep -n '\-notmatch' .claude/hooks/scripts/clang-format.ps1` 返回空
- `grep -n '\-notmatch' .claude/hooks/scripts/pre-tool-use.ps1` 返回空
- 两文件均含 `ConvertFrom-Json` 调用
- PowerShell 语法检查通过

### Task 2: 修复 Shell Hook 脚本

**read_first:**
- .claude/hooks/scripts/clang-format.sh
- .claude/hooks/scripts/pre-tool-use.sh

**action:**
1. 读取两个 .sh 文件
2. 找到使用 `sed` 提取 JSON 字段的代码段
3. 替换为 jq（如果可用）：
   ```bash
   filePath=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
   [ -z "$filePath" ] && exit 0
   ```
4. 若 jq 不可用，使用 Python fallback（参考现有 encoding-bridge.py 模式）

**acceptance_criteria:**
- `grep -n "sed.*file_path\|grep.*file_path" .claude/hooks/scripts/*.sh` 不应再出现在 JSON 提取上下文中
- 两 .sh 文件含 `jq` 或 Python JSON 解析
- Shell 语法检查：`bash -n FILE` 通过

### Task 3: 提交 + 推送

**action:**
1. 创建 02-02-SUMMARY.md
2. git add + commit
3. git push

**acceptance_criteria:**
- 中文提交信息引用 TECHD-08
- 4 个文件都已修改并提交
- 已推送到 origin/master

## Commit Message

```
fix(02-02): Hook 脚本使用 ConvertFrom-Json/jq 替代正则解析

修复 TECHD-08 脆弱性。4 个 Hook 脚本用 sed/正则从 stdin 提取 JSON
字段，转义字符、嵌套结构时会失败。

PowerShell: `ConvertFrom-Json`
Shell: `jq` (含 Python fallback)

保留 `exit 0` 失败不阻塞语义。

影响文件:
- .claude/hooks/scripts/clang-format.{ps1,sh}
- .claude/hooks/scripts/pre-tool-use.{ps1,sh}
```

## Verification

```bash
# 验证正则解析已移除
grep -rn '"file_path".*:-notmatch\|sed.*file_path' .claude/hooks/scripts/ && echo "FAIL" || echo "PASS"

# 验证 ConvertFrom-Json/jq 已加入
grep -rn "ConvertFrom-Json\|jq.*file_path" .claude/hooks/scripts/
```

## Artifacts This Phase Produces

- 修改: 4 个 Hook 脚本（2 .ps1 + 2 .sh）
- 新增: 02-02-SUMMARY.md
