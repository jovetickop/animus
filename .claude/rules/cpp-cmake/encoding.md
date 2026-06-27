# GBK 编码支持

## 概述

针对 Windows 平台 C/C++ 项目中使用 GBK 编码（含 GB2312/GB18030）的场景，
harness 通过 hooks 自动处理编码转换，AI 工具链全程使用 UTF-8 内部表示。

## 自动编码转换

| 钩子阶段 | 转换方向 | 说明 |
|---------|---------|------|
| PreToolUse (Write/Edit 前) | GBK → UTF-8 | 将 GBK 编码文件转为 UTF-8，确保 AI 正确读取和修改 |
| PostToolUse (Write/Edit 后) | UTF-8 → GBK | clang-format 格式化后自动转回 GBK，保持项目原始编码 |

无需手动干预。在项目 `.claude/harness/project-config.json` 中设置 `"encoding": "gbk"` 即可启用。

## Linux 编译说明

如果项目需要在 Linux 下编译且源文件为 GBK 编码，请在 CMakeLists.txt 中添加编译选项：

```cmake
# 通知 GCC/Clang 源文件为 GBK 编码，生成的可执行文件使用 UTF-8
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -finput-charset=gbk -fexec-charset=utf-8")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -finput-charset=gbk -fexec-charset=utf-8")
```

如果使用 MSVC 编译 Windows 版本，通常无需额外配置，MSVC 默认使用系统本地编码。

## 注意事项

- **Agent 不需要手动转换编码**：hooks 会自动完成 GBK ↔ UTF-8 转换，不要在 Agent 指令中编写编码转换逻辑。
- 如果已经启用 GBK 但出现乱码，请检查 `project-config.json` 中的 `"encoding"` 字段是否正确设置。
- 临时查看文件编码：`file --mime-encoding <filename>`
