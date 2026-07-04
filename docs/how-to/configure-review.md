---
type: how-to
audience: plugin-developer
---

# 如何调整代码审查严格度

> 通过修改 `config.toml` 控制审查的行为和严格程度。

---

## 修改严格度

在 `.claude/animus/config.toml` 中：

```toml
[review]
strictness = "low"       # low / normal / high
max_findings = 20        # 每次审查最多输出多少条
skip_categories = []     # 跳过的审查类别
```

| 严格度 | 行为 |
|--------|------|
| `low` | 仅标记 HIGH 级问题，MEDIUM/LOW 全部自动通过 |
| `normal` | 检查 HIGH+MEDIUM，LOW 自动通过（推荐） |
| `high` | 所有级别都必须修复才能通过 |

## 跳过某些审查类别

```toml
# 跳过命名规范和格式化检查
skip_categories = ["naming", "formatting"]
```

可选值：`naming` / `formatting` / `performance` / `security`

## 验证生效

修改后执行：

```bash
python scripts/animus-engine.py validate
```

如果配置格式正确，会输出 `config.toml 校验通过`。
