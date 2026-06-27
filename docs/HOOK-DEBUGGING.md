# Hook 调试指南

## 概述

Claude Code 通过 `hooks.json` 注册 4 种钩子：
- **PreToolUse**: Write/Edit 前执行（备份 + 编码转换）
- **PostToolUse**: Write/Edit 后执行（格式化）
- **PreCompact**: 上下文压缩前执行（刷写进度）
- **Stop**: 会话结束时执行（检查未完成任务）

## 手动运行 Hook

### PreToolUse
```powershell
# 模拟 Write 工具调用
echo '{"tool_name":"Write","tool_input":{"file_path":"test.cpp"}}' | .claude/hooks/scripts/pre-tool-use.ps1
```

### PostToolUse (clang-format)
```powershell
echo '{"tool_name":"Write","tool_input":{"file_path":"test.cpp"}}' | .claude/hooks/scripts/clang-format.ps1
```

### 双平台测试
```bash
# Shell 版本（Linux/macOS）
echo '{"tool_name":"Write","tool_input":{"file_path":"test.cpp"}}' | .claude/hooks/scripts/clang-format.sh 2>/dev/null

# PowerShell 版本（Windows）
echo '{"tool_name":"Write","tool_input":{"file_path":"test.cpp"}}' | .claude/hooks/scripts/clang-format.ps1
```

## 调试模式

设置环境变量 `HARNESS_DEBUG=true` 启用调试输出：

```bash
export HARNESS_DEBUG=true
# 或 PowerShell:
$env:HARNESS_DEBUG = "true"
```

调试模式下会输出：
- 文件路径解析结果
- 编码转换详情
- 格式化工具调用参数

## 常见问题

### Hook 脚本静默失败
`hooks.json` 的三重短路逻辑（`bash ... 2>/dev/null || powershell ... 2>/dev/null || exit 0`）会吞噬所有错误。
排查时手动运行 Hook 脚本查看输出。

### Shell 脚本执行失败
最常见原因：`.sh` 文件使用 CRLF 换行（已修复）。验证：
```bash
grep -l $'\r$' .claude/hooks/scripts/*.sh  # 应返回空
```

### JSON 解析失败
Hook 脚本从 stdin 接收 JSON。验证 stdin 内容：
```powershell
$input | Out-String  # 检查原始 JSON 格式
```

### clang-format 未生效
```bash
# 确认项目配置
cat .claude/harness/project-config.json  # encoding 字段
# 手动格式化
clang-format -i file.cpp
```
