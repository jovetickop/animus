# 02-01: 替换 Invoke-Expression 为安全调用

**Plan ID:** 02-01
**Wave:** 1（与 02-02、02-03 并行）
**TECHD:** TECHD-07
**Autonomous:** true
**Files Modified:**
- .claude/templates/harness/run-regression.ps1

## Objective
消除 `run-regression.ps1` 中 3 处 `Invoke-Expression` 调用，替换为 PS 5.1 兼容的安全命令执行方式。

## Research Summary
- 使用 `& $cmd` 调用运算符 + `Split(' ', 2)` 分离 exe 与 args
- 保持 PS 5.1 兼容
- 行为不变，注入风险消除

## Tasks

### Task 1: 替换 run-regression.ps1 中的 Invoke-Expression

**read_first:**
- .claude/templates/harness/run-regression.ps1
- .planning/phases/02-security-robustness/02-RESEARCH.md

**action:**
1. 读取 .claude/templates/harness/run-regression.ps1
2. 找到第 16、24、40 行附近的 `Invoke-Expression $xxxCmd` 调用
3. 替换为：
   ```powershell
   $parts = $buildCmd.Split(' ', 2)
   & $parts[0] $parts[1]
   ```
4. 同理处理 $testCmd
5. 保留所有错误处理和退出码逻辑

**acceptance_criteria:**
- `grep -n "Invoke-Expression" .claude/templates/harness/run-regression.ps1` 返回空
- PowerShell 语法检查通过：`powershell -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw '.claude/templates/harness/run-regression.ps1'), [ref]$null); 'ok'"`
- 文件仍然有 3 处命令执行位置，行为等价

### Task 2: 创建 SUMMARY 并提交

**action:**
1. 创建 .planning/phases/02-security-robustness/02-01-SUMMARY.md
2. git add + commit
3. git push

**acceptance_criteria:**
- 提交信息中文，包含 "TECHD-07" 引用
- 已推送到 origin/master

## Commit Message

```
fix(02-01): 替换 run-regression.ps1 中的 Invoke-Expression

修复 TECHD-07 安全隐患。`Invoke-Expression` 从 JSON 配置文件
读取命令字符串并执行，存在命令注入风险。

替换为 `& $parts[0] $parts[1]` 调用运算符，安全且 PS 5.1 兼容。
行为等价，错误处理保留。

影响文件: .claude/templates/harness/run-regression.ps1
```

## Verification

```bash
grep -n "Invoke-Expression" .claude/templates/harness/run-regression.ps1
# 应返回空
```

## Artifacts This Phase Produces

- 修改: `.claude/templates/harness/run-regression.ps1`（3 处替换）
- 新增: `.planning/phases/02-security-robustness/02-01-SUMMARY.md`
