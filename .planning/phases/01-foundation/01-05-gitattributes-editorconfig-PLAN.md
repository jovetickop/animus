---
phase: "01-foundation"
plan: "05"
type: "execute"
wave: 4
depends_on:
  - "01-01"
  - "01-02"
  - "01-04"
files_modified:
  - ".gitattributes"
  - ".editorconfig"
autonomous: true
requirements:
  - "TECHD-11"
must_haves:
  truths:
    - ".gitattributes 存在且正确配置 .sh/.ps1/.py/.json/.md 等文件类型的换行符"
    - ".editorconfig 存在且配置编辑器统一行为"
    - "git add --renormalize . 后所有文件换行符符合 .gitattributes 规定"
  artifacts:
    - path: ".gitattributes"
      provides: "Git 属性配置（换行符规范化）"
    - path: ".editorconfig"
      provides: "编辑器配置（统一代码风格）"
  key_links:
    - from: ".gitattributes"
      to: "仓库根目录"
      via: "Git 自动应用"
      pattern: "\\.sh.*eol=lf|\\.ps1.*eol=crlf"
---

<objective>
添加 .gitattributes 和 .editorconfig 作为基础设施制度性保障，确保换行符和编码长期一致。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-foundation/01-RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: 创建 .gitattributes 文件</name>
  <files>.gitattributes</files>
  <read_first>.gitignore</read_first>
  <action>
创建 .gitattributes 文件，内容如下（根据 RESEARCH.md Q6）：

```
# 自动检测文本文件，统一为 LF
* text=auto

# Shell 脚本 - 必须 LF（跨平台 Unix shell 要求）
*.sh text eol=lf
*.bash text eol=lf

# PowerShell 脚本 - Windows 使用 CRLF
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
*.toml text eol=lf
*.ini text eol=lf

# 二进制文件 - 不转换
*.png binary
*.jpg binary
*.pdf binary
*.exe binary
*.dll binary
*.ico binary
```

注：.ps1 文件使用 CRLF 是因为 Windows PowerShell 5.1 传统，但 Git 会自动在检出时转换为 CRLF、在提交时转回 LF。配合 Phase 1 的编码转换，Git diff 将正确显示变更。
  </action>
  <acceptance_criteria>
- .gitattributes 文件存在于仓库根目录
- 包含 *.sh eol=lf 和 *.ps1 eol=crlf 配置
- 包含二进制文件声明
  </acceptance_criteria>
  <verify>
<automated>
echo "=== .gitattributes 存在性 ===" && ls -la .gitattributes && echo "=== 关键配置验证 ===" && grep -E "^\\*.sh|^\\*.ps1" .gitattributes
</automated>
  </verify>
  <done>.gitattributes 创建完成</done>
</task>

<task type="auto">
  <name>Task 2: 创建 .editorconfig 文件</name>
  <files>.editorconfig</files>
  <read_first>.gitignore</read_first>
  <action>
创建 .editorconfig 文件，标准化编辑器配置：

```
# EditorConfig is awesome: https://EditorConfig.org

# 顶层配置文件
root = true

# 所有文件
[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

# Markdown 文件
[*.md]
trim_trailing_whitespace = false

# PowerShell 脚本
[*.ps1]
end_of_line = crlf

# Shell 脚本
[*.sh]
end_of_line = lf

# Python 文件
[*.py]
indent_style = space
indent_size = 4

# JSON/YAML/TOML
[*.{json,yaml,yml,toml}]
indent_style = space
indent_size = 2

# CMake
[CMakeLists.txt]
indent_style = space
indent_size = 2
```
  </action>
  <acceptance_criteria>
- .editorconfig 文件存在于仓库根目录
- 包含 charset、end_of_line、indent_style 基本配置
  </acceptance_criteria>
  <verify>
<automated>
echo "=== .editorconfig 存在性 ===" && ls -la .editorconfig && echo "=== 关键配置验证 ===" && grep -E "charset|end_of_line|indent_style" .editorconfig | head -5
</automated>
  </verify>
  <done>.editorconfig 创建完成</done>
</task>

<task type="auto">
  <name>Task 3: 执行 git add --renormalize 并提交</name>
  <files>.gitattributes, .editorconfig</files>
  <read_first>.gitattributes, .editorconfig</read_first>
  <action>
执行 git renormalize 强制 Git 按照新的 .gitattributes 重新检测文件：

```bash
git add --renormalize .
git status
```

检查哪些文件会被提交，确保：
- .sh 文件显示为 modified（LF 换行符变更）
- .ps1 文件显示为 modified（如果之前未正确应用 CRLF）
- .gitattributes 和 .editorconfig 显示为 new file

然后提交变更：
```bash
git commit -m "chore: add .gitattributes and .editorconfig for infrastructure consistency

- .gitattributes: standardize line endings (.sh=LF, .ps1=CRLF, .py=LF)
- .editorconfig: unify editor settings across team
- Run git add --renormalize to apply new attributes"
```
  </action>
  <acceptance_criteria>
- git status 显示 .gitattributes 和 .editorconfig 为新文件
- 相关脚本文件显示为 modified（换行符变更）
- commit 成功
  </acceptance_criteria>
  <verify>
<automated>
git status --short | head -20
</automated>
  </verify>
  <done>基础设施配置文件创建并提交完成</done>
</task>

</tasks>

<verification>
## Phase 1 Wave 4 基础设施验证

```bash
# 验证 .gitattributes 存在且格式正确
cat .gitattributes | head -20

# 验证 .editorconfig 存在且格式正确
cat .editorconfig | head -20

# 验证换行符规范化后 .sh 文件为 LF
file .claude/hooks/scripts/*.sh

# 验证换行符规范化后 .ps1 文件为 CRLF
file .claude/templates/harness/*.ps1 .claude/commands/*.ps1
```
</verification>

<success_criteria>
- .gitattributes 和 .editorconfig 存在且配置正确
- 所有 .sh 文件为 LF 换行符
- 所有 .ps1 文件为 CRLF 换行符
- Git 提交成功
</success_criteria>

<output>
创建 .planning/phases/01-foundation/01-05-SUMMARY.md
</output>