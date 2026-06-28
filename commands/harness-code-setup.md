---
description: 检测项目类型并为目标项目创建 .claude/harness-cc/ 运行时目录
---

# /harness-code-setup

在目标项目根目录执行以下命令来安装 CodeHarness 基础设施：

```powershell
& "${CLAUDE_PLUGIN_ROOT}\commands\harness-code-setup.ps1" -ProjectDir (Get-Location) -PluginRoot "${CLAUDE_PLUGIN_ROOT}"
```

脚本会自动检测项目类型、创建 `.claude/harness-cc/` 运行时目录、生成 `project-config.json` 项目配置、初始化空的状态文件。

初始化时默认写入 auto-update-plugin: true，可通过修改 .claude/harness-cc/project-config.json 中的 auto-update-plugin 字段关闭自动更新。
