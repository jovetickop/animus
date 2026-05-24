# 已有工程验收清单

> 完整验收流程请执行 `/harness-code-review`，本文件为人工快速参考。

## 通用检查

- [ ] 改动是否通过构建/编译？
- [ ] 相关测试是否执行并通过？
- [ ] 代码是否符合项目编码规范？
- [ ] 是否有未处理的错误路径？
- [ ] 是否有调试代码或临时日志残留？
- [ ] harness 状态是否已更新？（features.json + claude-progress.txt）

## 语言专项（按项目类型选做）

- **C++/Qt**：QObject 生命周期、MOC/UIC/RCC、UI 线程不阻塞、tr() 文案
- **Python**：依赖锁定、类型注解、pytest 覆盖
- **Node**：npm audit 无高危、ESLint 通过
- **Rust**：cargo clippy 无警告、unsafe 有 Safety 注释
