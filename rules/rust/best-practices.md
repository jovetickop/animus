# Rust 编码最佳实践

## Cargo 依赖管理

- 依赖版本使用语义化版本范围（`"1.2"`），锁定补丁版本。
- `[dev-dependencies]` 只用于测试代码，不要混入生产依赖。
- workspace crate 间引用使用 `path = "..."` 避免发布冲突。
- 引入新 crate 前评估维护活跃度和依赖树膨胀。

## Clippy 规范

- 所有代码必须通过 `cargo clippy -- -D warnings` 无警告。
- 不要使用 `#[allow(clippy::*)]` 绕过 lint，除非附注释说明原因。
- 优先使用 `clippy::pedantic` 和 `clippy::nursery` 中的合理 lint。

## unsafe 使用约束

- `unsafe` 必须封装在最小安全抽象（safe wrapper）内。
- 每个 `unsafe` 块必须附带 `// Safety: ...` 注释说明不变式。
- 对外 API 不允许直接暴露 unsafe 函数，除非有充分理由。

## 命名约定

- 类型、trait 使用 `PascalCase`；函数、方法、变量使用 `snake_case`。
- 常量使用 `SCREAMING_SNAKE_CASE`。
- 类型转换使用 `From`/`Into` trait，避免自定义 `as` 转换。

## 错误处理规范

- 域错误使用 `thiserror` 定义枚举类型。
- 顶层/边界错误处理使用 `anyhow::Result`。
- 避免裸 `unwrap()` 和 `expect()`；高频路径优先使用 `?` 运算符。
- 对于确定不会失败但类型系统无法表达的场景，附注释说明理由。

## 格式化

- 使用 `cargo fmt` 统一代码格式，禁止手动对齐。
- 每行不超过 100 字符。
- 提交前确保代码已通过 `cargo fmt --check`。
