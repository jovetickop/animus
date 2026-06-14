# 测试策略

_生成日期：2026-06-14_

## 测试框架与工具

### 推荐测试框架（按项目类型）

本项目是一个 **harness-cc 技能插件开发仓库**，本身不包含业务代码的测试。它通过 Agent 定义和规则文件为 **目标工程** 推荐测试框架和策略。

| 项目类型 | 首选测试框架 | 替代方案 | Agent |
|---------|------------|---------|-------|
| C++/Qt | QTest / CTest | GoogleTest | `.claude/agents/qt/test-engineer.md` |
| C++ (纯 CMake) | GoogleTest | CTest | `.claude/agents/universal/test-engineer.md` |
| Python 3 | pytest | pytest + pytest-cov | `.claude/agents/python/test-engineer.md` |
| Python 2 | unittest | — | `.claude/agents/python/test-engineer.md` |
| Node.js/Web | Vitest | Jest, Playwright | `.claude/agents/node/test-engineer.md` |
| Rust | cargo test | proptest, Miri | `.claude/agents/rust/test-engineer.md` |
| Go | go test | table-driven tests | `.claude/agents/go/test-engineer.md` |

### 测试命令配置 (`project-config.json`)

测试命令在 `.claude/templates/harness/project-config.json` 中声明，按前后端分离配置：

```json
{
  "backend": {
    "test-command": "cd backend && python -m pytest tests/ -v"
  },
  "frontend": {
    "test-command": "cd frontend && npm run test"
  }
}
```

命令保持空值，由用户首次使用时填写，不硬编码默认值。

### 验证脚本

| 脚本 | 位置 | 用途 |
|------|------|------|
| `run-regression.ps1` | `.claude/templates/harness/run-regression.ps1` | 一式构建 + 测试运行器，从 `project-config.json` 和 `features.json` 自动提取构建/测试命令 |
| `validate-features.ps1` | `.claude/commands/validate-features.ps1` | 验证 `features.json` 结构完整性（字段、ID唯一性、状态值合法性） |
| `check-consistency.ps1` | `.claude/commands/check-consistency.ps1` | 检查 `features.json` 与 `claude-progress.txt` 状态一致性 |
| `show-status.py` | `.claude/templates/harness/show-status.py` | 状态概览，含 Oracle 验证门控状态、任务统计、持续时间、失败趋势 |
| `session-catchup.py` | `.claude/scripts/session-catchup.py` | 会话恢复工具，扫描历史事件重建上下文 |

## 测试层级（单元/集成/E2E）

### 通用覆盖建议 (`.claude/rules/universal/testing.md`)

每个功能级任务至少考虑：
- 正常输入
- 空输入
- 无效输入
- 边界值
- 邻近逻辑的回归风险

### 语言专项要求

| 语言 | 单元测试 | 集成测试 | 额外要求 | Agent 文件 |
|------|---------|---------|---------|-----------|
| **C++/Qt** | QTest | smoke test / CTest | Qt UI 考虑最小 smoke test 或交互状态验证；长耗时/异步流程考虑事件循环、信号触发和超时 | `agents/qt/test-engineer.md` |
| **Python** | pytest | pytest + cov | 覆盖基线 `pytest --cov --cov-fail-under=80`；异步使用 `pytest-asyncio` 的 `@pytest.mark.asyncio`；文件 I/O 和网络调用必须 mock | `agents/python/test-engineer.md` |
| **Node/Web** | Vitest / Jest | E2E (Playwright) | 前端：组件测试 (Testing Library)；后端：supertest API 端点测试；Mock 策略分接口层/数据库层/第三方服务层 | `agents/node/test-engineer.md` |
| **Rust** | cargo test unit | cargo test integration / doc test | 对纯函数优先使用 proptest 属性测试；unsafe 代码必须用 Miri 验证；异步代码需要 tokio::test 运行时配置 | `agents/rust/test-engineer.md` |
| **Go** | go test (table-driven) | go test / benchmark | 优先 table-driven tests；并发代码使用 `go test -race`；公共函数补充 Example 测试 | `agents/go/test-engineer.md` |

### 测试类型定义

**Unit Tests（单元测试）**：
- 按语言标准框架编写，测试单个函数/模块的行为。
- Rust 中 `#[cfg(test)] mod tests { ... }` 内联在源文件中。
- Go 中 `*_test.go` 文件与被测文件同级放置。
- Python 中 `tests/` 目录结构对应模块层级。

**Integration Tests（集成测试）**：
- Rust 的 `tests/` 目录（外部集成测试）。
- Node.js 的 `tests/` 或 `__tests__/` 目录。
- 使用 mock/stub/fake 隔离外部依赖。

**E2E Tests（端到端测试）**：
- 仅 Node/Web 项目使用 Playwright。
- 其他语言不强制要求 E2E。

### 前端组件测试 (`frontend/component-guidelines.md`)

```tsx
describe('GoBoard', () => {
  it('渲染正确数量的交叉点', () => {
    render(<GoBoard size={19} />);
    expect(screen.getAllByRole('button').length).toBe(19 * 19);
  });

  it('点击可落子位置触发 onMove', () => {
    const onMove = jest.fn();
    render(<GoBoard size={9} onMove={onMove} />);
    fireEvent.click(screen.getAllByRole('button')[0]);
    expect(onMove).toHaveBeenCalled();
  });
});
```

## 测试覆盖策略

### 覆盖基线

| 语言 | 覆盖率要求 | 命令 |
|------|-----------|------|
| Python | `--cov-fail-under=80` | `pytest --cov --cov-fail-under=80` |
| Go | 无硬性基线，`go test -cover` 检查 | `go test -cover` |
| Rust | 无硬性基线 | `cargo test` |
| Node | 配置覆盖率工具并设定基线 | `vitest --coverage` / `jest --coverage` |

### Mock 策略

| 语言 | Mock 工具 | 策略 |
|------|----------|------|
| Python | `pytest-mock`（首选）、`unittest.mock`（存量兼容） | 文件 I/O 与网络调用必须 mock，不依赖真实外部资源 |
| Node | Mock 分三层（接口层、数据库层、第三方服务层） | 根据测试层级选择适当 mock 策略 |
| Go | `testing` 包或 `testify/mock` | 涉及接口的代码进行 Mock |
| Rust | 通过 trait 实现 mock | 依赖注入方式 |
| Qt | QSignalSpy / 事件模拟 | UI 测试通过信号验证 |

## 构建验证流程

### 验证策略层级 (`.claude/rules/universal/testing.md`)

按以下顺序执行验证：

1. **静态检查**：运行 linter、类型检查器或编译器。
2. **构建/打包验证**：确保项目可以正常构建。
3. **单元测试**：运行项目的单元测试框架。
4. **集成/端到端测试**：若有，运行以验证关键流程。
5. **人工验证**：对 UI 变更或行为变更补充人工检查。

### 任务通过规则

任务满足以下条件才能标记为 `passed`：
- 构建成功
- 相关测试通过
- 结果已经写入 `.claude/harness/claude-progress.txt`

如果构建或测试失败，先把失败摘要写入进度日志，再把任务回退到 `pending`。

### Oracle 验证门控

当 `project-config.json` 中 `verify.verify_enabled = true` 时，任务从 `in_progress` 转为 `passed` 前自动执行 `verify_command`：

- 验证通过（exit 0）→ 允许转为 `passed`
- 验证失败（exit 非 0）→ 自动转为 `failed`
- 验证超时（`verify_timeout_seconds`，默认 120s）→ 自动转为 `failed`
- 验证输出写入 `claude-progress.txt`

相关配置字段（`.claude/templates/harness/project-config.json`）：
```json
{
  "verify": {
    "verify_enabled": false,
    "verify_command": "",
    "verify_timeout_seconds": 120
  }
}
```

### 验证命令契约

- `verify_command` 必须由脚本独立执行，AI 不可修改。
- run-regression.ps1 会依次执行 `build-command` 和 `test-command`（从 `project-config.json` 读取），任一失败则 `exit 1`。
- 若 `features.json` 中配置了 `test_command`，也会执行。

### 代码审查中的验证要求 (`.claude/agents/universal/code-reviewer.md`)

- 不得标记任务为 `passed` 之前跳过验证。
- 必须执行 `verify_command` 并确认 `exit 0`。
- 将验证输出写入 `claude-progress.txt`（至少最后 3 行）。
- 不得修改 `verify_config` 中的 `verify_command`。

## 持续集成中的测试

### 本仓库的 CI

本仓库没有构建步骤和 CI 配置。CI 通常在 **多语言目标工程** 上运行。

### 修改技能后的全语言回归

修改 harness 技能后需走 **全语言回归验证**（CLAUDE.md 中约定）：

- 至少创建 **3 种语言** 的临时仓库（C++/Qt、Rust、Python）。
- 每种语言走完整工作流：Setup → Plan → Implement（编译+测试）→ Review → Verify → git commit。
- 最后运行 `skill-creator` 评估全部通过后才能报告完成。

### 语言专项验证命令总结

| 语言 | Lint/静态检查 | 构建 | 测试 | 额外 |
|------|-------------|------|------|------|
| C++ | clang-tidy, cmake --build | cmake --build | ctest | sanitizers (-fsanitize=address,undefined) |
| Qt | MOC/UIC/RCC | cmake --build | QTest / ctest | 信号槽连接检查 |
| Python | flake8/mypy | — | pytest --cov --cov-fail-under=80 | pip install -r requirements.txt |
| Node | ESLint | npm run build | vitest / jest / playwright | npm audit |
| Rust | cargo clippy -- -D warnings | cargo build | cargo test (+ Miri for unsafe) | cargo fmt --check |
| Go | go vet | go build | go test -race -cover | go fmt |

### 基础设施脚本

| 脚本 | 路径 | 功能 |
|------|------|------|
| format-all.py | `.claude/hooks/scripts/format-all.py` | 多语言格式化分发（black/prettier/cargo fmt/clang-format） |
| encoding-bridge.py | `.claude/hooks/scripts/encoding-bridge.py` | GBK/UTF-8 编码桥接 |
| pre-tool-use.sh/ps1 | `.claude/hooks/scripts/pre-tool-use.sh` | Write/Edit 前备份 `features.json` |
| pre-compact.sh/ps1 | `.claude/hooks/scripts/pre-compact.sh` | 上下文压缩前刷写进度 |
| stop-check.sh/ps1 | `.claude/hooks/scripts/stop-check.sh` | 会话结束时检查未完成任务 |

### Hooks 自动化验证支持 (`hooks.json`)

`hooks.json` 中注册了 4 个自动化钩子：

- **PreToolUse**（Write/Edit 前）：自动备份 `features.json` 到 `.bak.时间戳`（保留最近 5 个）；GBK 编码项目自动将源文件转为 UTF-8。
- **PostToolUse**（Write/Edit 后）：自动运行 clang-format 格式化 C/C++ 代码；运行 format-all.py 多语言格式化；GBK 项目将文件转回 GBK。
- **PreCompact**（上下文压缩前）：向 claude-progress.txt 追加 [COMPACT] 时间戳标记行。
- **Stop**（会话结束/退出时）：检查是否有 `in_progress` 状态的未完成任务。

所有钩子以 `exit 0` 保证不阻塞主流程，同时提供 `.ps1` 和 `.sh` 双平台版本。

---

_测试策略分析：2026-06-14_
