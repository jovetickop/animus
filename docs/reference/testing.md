---
type: reference
audience: regular-user
---

# 测试参考

> Animus 插件自身的测试体系 — 运行方式、测试文件分布、覆盖范围。

---

## 运行测试

```bash
# 运行全部测试
pytest tests/

# 运行单个测试文件
pytest tests/test_engine.py

# 运行特定测试用例
pytest tests/test_engine.py -k "test_transition"

# 含覆盖率报告
pytest tests/ --cov=scripts/
```

---

## 测试文件分布

共 192+ 个单元测试，全部兼容 Python 2/3。

| 测试文件 | 覆盖范围 | 用例数 |
|----------|---------|--------|
| `tests/test_config_loader.py` | 配置加载（默认值、合并、校验、兼容） | 34 |
| `tests/test_engine.py` | 状态机流转、校验、DAG 检测 | 23 |
| `tests/test_engine_extras.py` | 推荐引擎、归档、重建、memlog | 12 |
| `tests/test_deferred_work.py` | deferred-work 读写、清空、Unicode | 10 |
| `tests/test_hooks.py` | write-gate、pre-tool-use、pre-compact、stop-check、clang-format | 26 |
| `tests/test_templates.py` | task_helpers、git_helper、report_generator、coding_session、init | 71 |
| `tests/test_animus_init.py` | 项目类型检测、TOML 生成、目录创建、不覆盖 | 16 |

---

## 测试规范

### 文件系统隔离

所有测试使用 `tempfile` 隔离文件系统操作，不写染工作目录。

### Python 2/3 兼容

测试代码保持与主代码相同的兼容要求：Python 2.7+ / 3.x，使用 `from __future__ import` 和兼容性辅助函数。

### 测试数据

共享测试数据放在 `tests/fixtures/` 目录下：

```
tests/fixtures/
  ├── plugin-valid/         ← 完整有效的 mock 插件结构
  └── plugin-invalid/       ← 含缺陷的 mock 插件结构（用于验证器测试）
```

---

## 持续集成

CI 步骤中运行：

```bash
# 质量门禁
npm run quality
# 或手动
npm test
```
