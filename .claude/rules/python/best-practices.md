# Python 编码最佳实践

## Python 版本选择

- 新项目默认使用 **Python 3**，不再支持 Python 2（已于 2020 年 EOL）。
- 存量 Python 2 项目逐步迁移，迁移期间避免混用版本不兼容语法。
- 需 Python 2/3 双兼容的脚本使用 `from __future__ import print_function` 等兼容层。
- 系统级工具脚本建议兼容 Python 2.7+ 和 3.x，shebang 使用 `#!/usr/bin/env python`。

## PEP 8 风格指南

- 缩进统一使用 4 空格，禁止 Tab。
- 行宽不超过 88 字符（兼容 `black` 默认值）。
- 类定义前后空两行，函数定义前后空一行。
- 二元运算符前换行，保持操作符对齐。

## import 规范

- 分组顺序：标准库 → 第三方 → 本地模块，每组空一行。
- 禁止使用 `from module import *`。
- 优先使用绝对导入，相对导入仅在包内子模块中使用 `from . import`。
- 同类导入建议合并：`from os import path, getcwd`。

## 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| 变量/函数 | `snake_case` | `current_index` |
| 类名 | `PascalCase` | `UserService` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| 私有成员 | 前导下划线 | `_internal_cache` |
| 模块名 | 短小全小写 | `data_loader.py` |
| 包名 | 短小全小写，无下划线 | `utils` |

## 类型注解要求

- 所有 public 函数的参数和返回值必须有类型注解。
- 使用 `from __future__ import annotations` 延迟求值。
- 复杂类型使用 `TypeAlias` 命名：`JsonDict: TypeAlias = dict[str, Any]`。
- 避免过度泛型，`Any` 使用前优先考虑 `object` 或 `Protocol`。

## 依赖管理规范

- 生产依赖写入 `pyproject.toml` 的 `[project.dependencies]`。
- 开发依赖写入 `[project.optional-dependencies] dev` 组。
- 锁定文件（`poetry.lock` / `uv.lock`）必须纳入版本控制。
- 新增依赖前优先确认标准库是否已有替代方案。
