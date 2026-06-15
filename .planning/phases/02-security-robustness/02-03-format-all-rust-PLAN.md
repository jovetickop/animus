# 02-03: 修复 format-all.py Rust 双重 fmt

**Plan ID:** 02-03
**Wave:** 1（与 02-01、02-02 并行）
**TECHD:** TECHD-09
**Autonomous:** true
**Files Modified:**
- .claude/hooks/scripts/format-all.py

## Objective
移除 `format-all.py` 中冗余的 `cargo fmt --check` + `cargo fmt` 调用，添加 `Cargo.toml` 目录查找缓存。

## Research Summary
- 移除第 68-84 行的双重调用
- 添加模块级 `_cargo_root_cache` 字典缓存
- 行为等价但显著减少 I/O

## Tasks

### Task 1: 修改 format-all.py

**read_first:**
- .claude/hooks/scripts/format-all.py

**action:**
1. 读取 format-all.py 找到 `format_rust` 函数（约第 68-84 行）
2. 移除 `subprocess.run(["cargo", "fmt", "--check"], ...)` 调用
3. 保留 `subprocess.run(["cargo", "fmt"], ...)` 单次调用
4. 添加 Cargo.toml 缓存：
   ```python
   _cargo_root_cache = {}

   def find_cargo_root(start_path):
       if start_path in _cargo_root_cache:
           return _cargo_root_cache[start_path]
       # ... 向上遍历逻辑
       _cargo_root_cache[start_path] = result
       return result
   ```
5. 验证无破坏其他功能

**acceptance_criteria:**
- `grep -n "fmt --check" .claude/hooks/scripts/format-all.py` 返回空
- 文件包含 `_cargo_root_cache` 字典
- Python 语法检查：`python -m py_compile .claude/hooks/scripts/format-all.py` 通过
- `format_rust` 函数调用 `cargo fmt` 一次

### Task 2: 提交 + 推送

**action:**
1. 创建 02-03-SUMMARY.md
2. git add + commit
3. git push

**acceptance_criteria:**
- 中文提交信息引用 TECHD-09
- 已推送到 origin/master

## Commit Message

```
perf(02-03): 修复 format-all.py Rust 双重 fmt + 缓存

修复 TECHD-09。每次 PostToolUse 触发 cargo fmt 时：
- 移除冗余的 `cargo fmt --check` 调用（结果被忽略）
- 添加 `_cargo_root_cache` 字典缓存 Cargo.toml 目录查找
- 减少 N 次 Rust 文件写入的 I/O 开销

影响文件: .claude/hooks/scripts/format-all.py
```

## Verification

```bash
# 验证 --check 已移除
grep -n "fmt --check" .claude/hooks/scripts/format-all.py && echo "FAIL" || echo "PASS"

# 验证缓存已添加
grep -n "_cargo_root_cache" .claude/hooks/scripts/format-all.py

# Python 语法
python -m py_compile .claude/hooks/scripts/format-all.py && echo "PASS" || echo "FAIL"
```

## Artifacts This Phase Produces

- 修改: .claude/hooks/scripts/format-all.py
- 新增: 02-03-SUMMARY.md
