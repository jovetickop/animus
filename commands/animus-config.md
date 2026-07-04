---
name: animus-config
description: 查看和修改 animus 配置
---

# `/animus-config` — 配置管理

## 功能

查看当前生效的配置、校验配置文件合法性。

## 用法

```
/animus-config            → 显示当前配置
/animus-config --validate → 校验 config.toml 合法性
```

## 流程

1. 调 `python scripts/config_loader.py` 读取三层合并后的配置
2. 输出格式化的配置信息（按配置段分组）
3. 带 `--validate` 时调 `python scripts/config_loader.py --validate`

## 输出示例

```
animus 配置（三层合并结果）
==============================
[dev]
  default_path = auto
  autonomous = false

[review]
  strictness = normal
  skip_categories = []
  max_findings = 20

[gates]
  require_task_before_write = true

[ponytail]
  enabled = true
  max_lines_per_file = 500

[party_mode]
  default_mode = subagent
  default_party = arch-review
  ...
```

## 配置覆盖原则

`defaults（硬编码） ← config.toml`

## 相关文件

- `.claude/animus/config.toml` — 团队配置

- `scripts/config_loader.py` — 加载逻辑
