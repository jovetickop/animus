# 编码规范与约定

_生成日期：2026-06-14_

## 语言级规范

本仓库是一个 **Claude Code 技能插件 `harness-cc` 的开发仓库**，不包含业务工程文件。所有代码、脚本、模板和 Agent 定义都集中在 `.claude/` 子目录中。规范文件本身以 Markdown 文档的形式存在，按语言组织在 `.claude/rules/` 下。

支持的语言插件及其专属规范：

| 语言 | 规范文件 | 范围 |
|------|---------|------|
| 通用 (Universal) | `.claude/rules/universal/coding-style.md` | 所有项目共用 |
| C++/CMake | `.claude/rules/cpp-cmake/best-practices.md` | 纯 C++ 项目 |
| C++/Qt | `.claude/rules/qt/best-practices.md` | C++/Qt 项目 |
| Python | `.claude/rules/python/best-practices.md` | Python 项目 |
| Node/TypeScript | `.claude/rules/node/best-practices.md` | Node/Web 项目 |
| Rust | `.claude/rules/rust/best-practices.md` | Rust 项目 |
| Go | `.claude/rules/go/best-practices.md` | Go 项目 |
| 前端组件 | `.claude/rules/frontend/component-guidelines.md` | React/Vue 组件 |
| Qt UI 架构 | `.claude/rules/qt/ui-architecture.md` | Qt 界面布局 |
| GBK 编码 | `.claude/rules/cpp-cmake/encoding.md` | Windows 中文编码 |

### C++ 标准选择 (`.claude/rules/cpp-cmake/best-practices.md`)

- 新项目默认 **C++17**，需 concepts/ranges/coroutines 时用 C++20。
- `CMakeLists.txt` 中显式声明 `set(CMAKE_CXX_STANDARD 17)` 和 `set(CMAKE_CXX_STANDARD_REQUIRED ON)`。
- CMake 最低版本要求 `3.21`。
- 启用 `CMAKE_EXPORT_COMPILE_COMMANDS` 方便静态分析。
- 使用 `target_include_directories`、`target_link_libraries` 替代全局设置。
- 使用 `FetchContent` 管理第三方依赖。

### Python 标准 (`.claude/rules/python/best-practices.md`)

- 新项目默认 Python 3；系统工具脚本需兼容 Python 2.7+ 和 3.x。
- 遵循 PEP 8 风格，行宽 88 字符（兼容 `black`）。
- 所有 public 函数必须有类型注解。
- import 顺序：标准库 → 第三方 → 本地模块，每组空一行。
- 禁止 `from module import *`。

### Node/TypeScript 标准 (`.claude/rules/node/best-practices.md`)

- ESLint 使用 `@typescript-eslint` 规则集，Prettier 负责格式化。
- 前端默认 Vite，库工具包优先使用 tsup 或 esbuild。
- 锁定依赖版本，定期运行 `npm audit`。
- CI 中加入 `lint` 步骤。

### Rust 标准 (`.claude/rules/rust/best-practices.md`)

- 所有代码必须通过 `cargo clippy -- -D warnings` 无警告。
- `unsafe` 必须封装在安全抽象内，每个 `unsafe` 块附 `// Safety: ...` 注释。
- 域错误使用 `thiserror`，顶层使用 `anyhow::Result`。
- 使用 `cargo fmt` 统一格式，每行不超过 100 字符。

### Go 标准 (`.claude/rules/go/best-practices.md`)

- 使用 Go 1.21+，代码必须通过 `gofmt` 格式化。
- 使用 `go vet` 静态检查。
- 使用 `error` 返回值而非 panic；库代码禁止 panic。

### GBK 编码支持 (`.claude/rules/cpp-cmake/encoding.md`)

- 在 `.claude/harness/project-config.json` 中设置 `"encoding": "gbk"` 启用。
- PreToolUse 钩子自动 GBK → UTF-8 转换，PostToolUse 自动 UTF-8 → GBK 回转。
- Agent 不需手动编码转换，hooks 自动完成。

## 命名约定

### 通用命名 (`universal/coding-style.md`)

| 类型 | 规则 | 示例 |
|------|------|------|
| 类型/类/接口 | `PascalCase` | `UserManager` |
| 函数/方法 | `camelCase` 或 `snake_case` | `loadProject()` |
| 局部变量 | `snake_case` 或 `camelCase` | `current_index` |
| 常量/枚举 | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| 文件名 | `snake_case` 或 `kebab-case` | `user_manager` |
| 私有成员 | 前导下划线 | `_cache` |

### 语言特殊约定

| 语言 | 约定 | 文件 |
|------|------|------|
| Go 包名 | 全小写，简短无下划线 | `.claude/rules/go/best-practices.md` |
| Go 文件 | snake_case | `user_service.go` |
| Go 测试文件 | `*_test.go` | `user_service_test.go` |
| Python 模块 | 短小全小写 | `data_loader.py` |
| Node 目录 | 小写 kebab-case | `user-profile/` |
| 前端组件文件 | PascalCase | `GoBoard.tsx` |
| 前端 Hook 文件 | `use` 前缀 camelCase | `useGameState.ts` |

### Agent 定义文件命名

- Agent 文件位于 `.claude/agents/{lang}/` 目录，使用蛇形命名：`task-implementer.md`、`test-engineer.md`、`code-reviewer.md`。
- 新增 Agent 时需在 frontmatter 包含 `description` 字段——这是 Claude Code 触发 Agent 的关键匹配文本。

## 文件组织约定

### 通用组织原则 (`universal/coding-style.md`)

- 一个文件尽量只定义一个主要 public 类型。
- 目录组织优先按 **功能/领域** 划分，而非按文件类型堆砌。
- 模块/包内文件职责清晰，避免单文件承载多种不相关逻辑。

### 文件结构顺序

1. 文件头注释（如项目要求）
2. 引用保护 / `#pragma once`
3. 系统库 / 标准库引用
4. 第三方库引用
5. 项目内头文件引用
6. 前置声明
7. 常量 / 类型定义
8. 类声明

额外约束：
- 外部库使用 `<...>`，项目内头文件使用 `"..."`。
- 实现文件第一行通常是对应的头文件。
- 能前置声明的类型优先前置声明。

### 前端组件组织 (`frontend/component-guidelines.md`)

```
components/
  GoBoard/
    GoBoard.tsx          # 组件逻辑
    GoBoard.module.css   # 组件样式
    GoBoard.test.tsx     # 测试
    index.ts             # 导出
```

### 仓库根结构（本仓库）

```
ty-qt-ai-plugin/
├── SKILL.md                          # 技能入口
├── README.md                         # 中文使用文档
├── .gitignore                        # 排除 CLAUDE.md、settings、worktrees
└── .claude/                          # 插件主资产目录
    ├── commands/                     # 3 个斜杠命令
    ├── agents/                       # 20 个 Agent 定义
    ├── rules/                        # 10 个规则文件
    ├── hooks/                        # PostToolUse 钩子
    ├── skills/tdd-workflow/          # 子技能
    └── templates/                    # 安装模板
```

### Python import 顺序 (`python/best-practices.md`)

分组顺序：**标准库 → 第三方 → 本地模块**，每组空一行。
优先使用绝对导入，相对导入仅在包内子模块中使用 `from . import`。

## 注释规范

### 通用注释原则 (`universal/coding-style.md`)

- 注释优先解释 **"为什么"**，不要重复代码已经表达清楚的"做了什么"。
- 注释默认使用 **中文**，保持简洁、明确。
- 公共接口、复杂状态机、线程边界、资源释放点建议补充注释。
- `TODO` 必须写清楚后续动作，不要只留"待优化"。
- 本项目所有源代码、Agent 定义、规范文件均使用中文注释。

### Rust unsafe 注释 (`rust/best-practices.md`)

每个 `unsafe` 块必须附带 `// Safety: ...` 注释说明不变式。

### 前端组件注释 (`frontend/component-guidelines.md`)

所有组件和关键函数必须有中文注释：

```tsx
/**
 * 围棋棋盘组件
 * 支持19路/13路/9路棋盘渲染，点击落子功能
 */
function GoBoard({ size, onMove }: GoBoardProps) {
  // 处理用户点击落子事件
  const handleClick = (x: number, y: number) => {
    // 检查是否可落子
    if (isValidMove(x, y)) {
      onMove({ x, y });
    }
  };
}
```

## 格式要求

### 通用格式 (`universal/coding-style.md`)

- 统一 **4 空格缩进**，禁止使用 Tab。
- 类、函数、`if/for/while/switch` 的左大括号换行。
- 单行 `if/for` 在逻辑非常简单时可省略大括号；多行分支必须加大括号。
- 每行不超过 **100 个字符**（Python 例外：88 字符兼容 `black`）。
- 连续空行不超过 1 行。
- 格式统一交给格式化工具，不要手动对齐。

### 自动格式化

- **C/C++**：`hooks.json` 注册了 PostToolUse 钩子，每次 Write/Edit 后自动运行 `clang-format`（`.claude/templates/.clang-format` 配置）。
- **多语言格式化**：`format-all.py` 自动根据文件扩展名分发到 black/prettier/cargo fmt/clang-format。
- 钩子两条平台分支（bash + PowerShell）互为降级，失败时 `exit 0` 不阻塞。
- 超时限制 10-15 秒，由 `hooks.json` 中的 `timeout` 控制。

### 语言特定格式

| 语言 | 格式化工具 | 额外要求 | 文件 |
|------|-----------|---------|------|
| C++ | clang-format | MSVC `/W4`, GCC/Clang `-Wall -Wextra -Wpedantic` | `rules/cpp-cmake/best-practices.md` |
| Go | gofmt / go fmt | `go vet` 静态检查 | `rules/go/best-practices.md` |
| Rust | cargo fmt | `cargo clippy -- -D warnings` | `rules/rust/best-practices.md` |
| Node | Prettier | ESLint `@typescript-eslint` | `rules/node/best-practices.md` |
| Python | black | 88 字符行宽 | `rules/python/best-practices.md` |

## Git 工作流规范

### Commit 消息格式 (`.claude/rules/universal/git-workflow.md`)

使用 **Conventional Commits** 风格：

```
<type>: <task id><简要描述>

<简要变更说明>
- <变更点 1>
- <变更点 2>

<Footer>
Co-authored-by: <Name>
```

- `task id` 可选，例如 `T013 `（注意后面有空格）。
- 标题一句话说清"做了什么"。
- 正文用要点列出关键改动与影响。

推荐类型：`feat`、`fix`、`refactor`、`docs`、`test`、`chore`、`perf`、`ci`。

### 分支与变更约束

- 每次改动保持聚焦，便于 review。
- 开 PR 前先检查完整分支差异。
- 当工作流、模板或命令变化时，同步更新文档。
- 每个任务在验收通过后都要提交并推送。

### 本仓库特殊约定 (CLAUDE.md)

- **不在本仓库自动 push 远程**，只本地提交，由用户自行推送。
- 修改 harness 技能后需走 **全语言回归**：至少 3 种语言（C++/Qt、Rust、Python）跑完整工作流。
- 用户全局规则：跨 Git 目录时执行 `codegraph sync`。

### 提交前检查

- 构建通过。
- 相关测试通过。
- 已清理调试代码和临时日志。
- Commit 信息与实际改动一致。

## 代码审查标准

### 审查流程 (SKILL.md / `agents/universal/code-reviewer.md`)

审查由 `code-reviewer` agent 执行，分四个维度：

1. **代码质量**：命名清晰且符合项目风格；文件组织高内聚低耦合；函数单一职责；无深层嵌套（超过 4 层应提前返回或拆函数）；错误处理完整；无魔法数字、硬编码路径或凭据。
2. **测试覆盖**：新增行为补充对应测试；覆盖正常输入、空/无效输入和边界值；测试独立重复运行，不依赖外部状态。
3. **安全性**：无硬编码密钥/令牌/密码；用户输入经校验或转义；错误信息不泄露敏感细节。
4. **变更影响**：改动未波及无关模块；配置、接口或资源路径变化同步更新引用方。

### 严重级别输出

- **critical/high**：必须修复后才能继续。
- **medium/low**：记录待办后可继续。

### 验收审查 (`harness-code-review` 命令)

执行 `/harness-code-review` 进行：通用检查（构建+测试+代码质量）+ 按项目类型的语言专项检查。辅助验证脚本：
- `.claude\commands\validate-features.ps1` — 验证 `features.json` 结构。
- `.claude\commands\check-consistency.ps1` — 检查 `features.json` 与 `claude-progress.txt` 状态一致性。

### 状态机验收硬规则 (CLAUDE.md)

- `in_progress → passed` 必须有构建/测试证据。
- 不得标记任务为 `passed` 之前跳过验证。
- 必须执行 `verify_command` 并确认 `exit 0`。
- 验证输出写入 `claude-progress.txt`（至少最后 3 行）。
- 不得修改 `verify_config` 中的 `verify_command`。

### 已有工程验收清单 (`.claude/templates/existing_project/review-checklist.md`)

通用检查项：
- [ ] 改动是否通过构建/编译？
- [ ] 相关测试是否执行并通过？
- [ ] 代码是否符合项目编码规范？
- [ ] 是否有未处理的错误路径？
- [ ] 是否有调试代码或临时日志残留？
- [ ] harness 状态是否已更新？

### 核心设计约束 (`universal/coding-style.md`)

- 访问修饰符必须显式写出。
- 函数名必须体现动作或结果，避免 `DoWork`、`ProcessData` 空泛命名。
- 参数数量控制在 4 个以内，过多时封装参数对象。
- 嵌套超过 4 层时优先提前返回、拆函数或抽策略。
- 禁止魔法数字，改用常量、枚举或具名配置。
- 优先使用 RAII 和智能指针管理资源。
- 裸指针只用于"不拥有对象"的场景。
- 避免带副作用的全局变量和静态初始化对象。

---

_编码规范分析：2026-06-14_
