# Phase 02 Plan 02: Hook 脚本 JSON 解析修复总结

**Plan:** 02-02
**Phase:** 02-security-robustness
**Requirement:** TECHD-08
**Status:** COMPLETED

## 变更概述

将 4 个 Hook 脚本中脆弱的 regex/sed JSON 解析替换为健壮的 `ConvertFrom-Json`（PowerShell）或 `jq` + Python fallback（Shell）。

## 修改文件

| 文件 | 修改前 | 修改后 |
|------|--------|--------|
| `clang-format.ps1` | `$inputJson -notmatch '"file_path"...'` | `ConvertFrom-Json` + try/catch |
| `pre-tool-use.ps1` | 多段 `-match` 正则提取 tool/name/file_path | `ConvertFrom-Json` 统一解析 |
| `clang-format.sh` | `sed -n 's/.*"file_path":"\([^"]*\)"...'` | `jq -r '.tool_input.file_path'` + Python fallback |
| `pre-tool-use.sh` | sed 提取 tool/name/file_path 三段 | `jq` + Python fallback |

## 技术细节

**PowerShell 模式：**
```powershell
try {
    $inputObj = $input | ConvertFrom-Json
    $filePath = $inputObj.tool_input.file_path
    if (-not $filePath) { exit 0 }
} catch {
    exit 0
}
```

**Shell 模式：**
```bash
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
if [ -z "$file_path" ] && command -v python >/dev/null 2>&1; then
    file_path=$(echo "$input" | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)
fi
[ -z "$file_path" ] && exit 0
```

## 验证结果

- PowerShell 语法检查：通过（PSParser 无报错）
- Shell 语法检查：`bash -n` 通过
- 旧正则模式：已全部移除（`-notmatch '"file_path'` 和 `sed.*file_path` 均无匹配）
- 新 JSON 解析：4 个文件均已加入
- `exit 0` 失败不阻塞语义：全部保留

## 提交

```
c8f10c5 fix(02-02): Hook 脚本使用 ConvertFrom-Json/jq 替代正则解析
```

**Commit hash:** `c8f10c5`
**Push:** 已推送到 origin/master