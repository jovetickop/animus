# 编码策略说明

## 为什么选择 UTF-8 with BOM

本仓库中所有 `.ps1` 文件统一使用 **UTF-8 with BOM**（字节顺序标记 `EF BB BF`）。

**原因：**
- PowerShell 5.1（Windows 内置版本）默认以系统本地编码读取无 BOM 的 UTF-8 文件
- 无 BOM 时 PS 5.1 在某些中文 Windows 环境下会将 UTF-8 解析为 GBK，导致中文乱码
- BOM 标记让 PowerShell 5.1+ 和 7+ 都能正确识别文件编码

## PowerShell 5.1 编码陷阱

| 操作 | 默认编码 | 问题 |
|------|---------|------|
| `Out-File` / `>` | UTF-16LE | 文件体积 2 倍，Git diff 不可读 |
| `Set-Content` | ANSI (GBK) | 跨平台不一致 |
| `Add-Content` | ANSI (GBK) | 同上 |

**原则：** 所有文件 I/O 必须显式指定 `-Encoding UTF8`：
```powershell
# 正确
Get-Content -Path file.ps1 -Encoding UTF8
Set-Content -Path file.ps1 -Encoding UTF8 -Value $content

# 错误（默认 UTF-16LE）
Get-Content -Path file.ps1
Out-File -FilePath file.ps1 -InputObject $content
```

## 文件编码对照

| 文件类型 | 编码 | 换行符 | 原因 |
|---------|------|--------|------|
| `.ps1` | UTF-8 with BOM | CRLF | PS 5.1 兼容性 |
| `.psm1` | UTF-8 with BOM | CRLF | PS 5.1 兼容性 |
| `.sh` | UTF-8 | LF | Linux/macOS 执行要求 |
| `.py` | UTF-8 | LF | Python 标准 |
| `.json` | UTF-8 | LF | 跨平台工具链 |
| `.md` | UTF-8 | LF | 文档标准 |
