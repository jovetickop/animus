---
description: 检测项目类型并复制对应工作流资产到目标工程
---

# /harness-code-setup

在目标项目根目录执行以下命令来安装 CodeHarness 基础设施：

```powershell
.\.claude\commands\harness-code-setup.ps1 -ProjectDir (Get-Location) -SkillDir "$env:USERPROFILE\.claude\skills\harness-cc"
```

脚本会自动检测项目类型、复制 agent/rule/command 文件、生成 project-config.json、处理 CLAUDE.md 合并。
