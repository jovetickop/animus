# 集成与外部依赖

**分析日期:** 2026-06-14

## 外部依赖清单

本仓库作为 Claude Code 技能插件，对目标项目无侵入式依赖。所有依赖为**工具链级别**：

| 依赖 | 类型 | 版本要求 | 用途 | 配置位置 |
|------|------|----------|------|----------|
| PowerShell | 运行时 | 5.1+ | 核心引擎（状态机、项目初始化、hook 脚本） | 系统安装 |
| Python | 运行时 | 2.7+ / 3.x | 辅助脚本（状态显示、编码转换、格式化分发、验证） | 系统安装 |
| Node.js | 运行时 | 任意 | 通过 npx 运行 MCP 服务器 | 系统安装 |
| Git | 工具链 | 任意 | 版本控制、提交 | 系统安装 |
| clang-format | 工具链 | 任意 | C/C++ 代码格式化 | 系统安装或 LLVM 包 |
| black | 工具链 | 任意 | Python 格式化（可选，降级到 autopep8） | pip install black |
| autopep8 | 工具链 | 任意 | Python 格式化（降级选项） | pip install autopep8 |
| prettier | 工具链 | 任意 | JS/TS 格式化（可选，降级到 eslint） | npm install -g prettier |
| eslint | 工具链 | 任意 | JS/TS 格式化（降级选项） | npm install -g eslint |
| cargo fmt | 工具链 | 任意 | Rust 格式化 | rustup component add rustfmt |

## MCP 服务器集成

**配置文件:** `.claude/templates/.mcp.json`

插件模板为每个目标项目预配置 4 个 MCP 服务器：

### 1. Filesystem MCP
- **包:** `@modelcontextprotocol/server-filesystem`
- **启动命令:** `cmd /c npx -y @modelcontextprotocol/server-filesystem .`
- **用途:** 读写 features.json 等状态文件，避免编码问题
- **认证:** 无
- **作用域:** 项目根目录 `.`

### 2. Git MCP
- **包:** `@modelcontextprotocol/server-git`
- **启动命令:** `cmd /c npx -y @modelcontextprotocol/server-git`
- **用途:** Git 操作集成（提交、状态检查等）
- **认证:** 无

### 3. Memory MCP
- **包:** `@modelcontextprotocol/server-memory`
- **启动命令:** `cmd /c npx -y @modelcontextprotocol/server-memory`
- **用途:** 对 harness-history.jsonl 进行语义查询，分析失败模式和任务趋势
- **认证:** 无

### 4. Linear MCP
- **包:** `@linear/mcp-server`
- **启动命令:** `cmd /c npx -y @linear/mcp-server`
- **用途:** Linear 问题跟踪集成，保存 issue、任务追踪
- **认证:** 环境变量 `LINEAR_API_KEY`（需要在目标项目中配置）

### MCP 服务器依赖关系
```
MCP 服务器需要通过 npx 调用，因此依赖：
Node.js 运行时 → npm/npx → @modelcontextprotocol/* 包 / @linear/mcp-server
```

## 第三方服务集成

### Linear（问题跟踪）

- **集成方式:** MCP 服务器 `@linear/mcp-server`
- **用途:** 保存 task issue、任务追踪
- **配置:** 需要 `LINEAR_API_KEY` 环境变量
- **权限:** `.claude/settings.local.json` 中白名单允许 `mcp__linear__save_issue`

### GitHub（远端仓库）

- **集成方式:** Git 命令
- **用途:** 代码托管、远程推送
- **来源:** `git clone https://github.com/jovetickop/Harness-CC.git`
- **配置:** 在 `.claude/settings.local.json` 中白名单允许 `Bash(git push *)` 和 `Bash(git remote *)`

## CI/CD 集成

**无 CI/CD 配置。** 本仓库没有以下任何 CI/CD 配置：
- GitHub Actions (无 `.github/` 目录)
- Azure Pipelines (无 `azure-pipelines*` 文件)
- GitLab CI (无 `.gitlab-ci.yml`)
- Jenkins (无 `Jenkinsfile`)
- Docker (无 `Dockerfile` 或 `docker-compose.yml`)

验证工作（全语言回归测试）通过 `scripts/run-regression.py` 手动执行。

## 数据流依赖关系

### 技能激活流程
```
用户输入 /harness-cc
  → SKILL.md 被读取
    → 检查 .claude/harness/ 是否存在
      → 不存在: 调用 init-project.ps1（复制资产）
        → 检测项目类型（CMake/Cargo/go.mod/package.json/pyproject.toml）
        → 复制 agent/rule/command 文件
        → 合并 CLAUDE.md 模板
      → 存在: 直接进入工作流
```

### 状态机数据流
```
features.json（任务列表）
  → update-progress.ps1 / update-progress.py（状态转换）
    → 状态校验（VALID_TRANSITIONS 表）
    → 依赖检查（depends_on 必须 passed）
    → 并发检查（parallel_group 同一组内只能一个 in_progress）
    → 写入 claude-progress.txt（进度日志）
    → 生成 docs/reports/<TaskId>-<name>.md（任务报告）
    → 可选: 执行 verify_command（Oracle 门控）
```

### Hook 触发数据流
```
Write/Edit 操作
  → PreToolUse hook
    → pre-tool-use.sh/ps1
      → 备份 features.json（保留最近 5 份）
      → 可选: encoding-bridge.py --action to_utf8（GBK→UTF-8）
  → Write/Edit 完成
  → PostToolUse hook
    → clang-format.sh/ps1（C/C++ 格式化）
    → format-all.py --file <path>（按扩展名分发格式化器）
    → 可选: encoding-bridge.py --action to_gbk（UTF-8→GBK）

上下文压缩
  → PreCompact hook
    → pre-compact.sh/ps1
      → 在 claude-progress.txt 追加 [COMPACT] 标记行

会话结束
  → Stop hook
    → stop-check.sh/ps1
      → 检查所有任务状态
      → 输出未完成任务恢复提示
```

### 会话恢复数据流
```
/clear 后 → session-catchup.py
  → 扫描 Claude Code session JSONL 文件
    → 找出最近的 features.json 写入事件
    → 找出进行中的任务
    → 输出恢复报告
```

## 状态文件依赖

| 文件 | 生产者 | 消费者 | 格式 |
|------|--------|--------|------|
| `state/features.active.json` | feature-planner agent | update-progress.ps1, show-status.py, session-catchup.py | JSON（活动任务） |
| `state/features.archive.json` | update-progress.ps1 | show-status.py | JSON（归档任务） |
| `state/features.json` | 旧版兼容 | update-progress.ps1 | JSON（兼容模式） |
| `state/claude-progress.txt` | update-progress.ps1, PreCompact hook | 人工读取 | 纯文本 |
| `harness/project-config.json` | setup 脚本 | run-regression.ps1, coding-session.ps1 | JSON |
| `harness/harness-history.jsonl` | update-progress.ps1 | show-status.py (失败趋势), Memory MCP | JSONL |

## 环境变量

| 变量 | 用途 | 必需 | 配置位置 |
|------|------|------|----------|
| `LINEAR_API_KEY` | Linear MCP 服务器认证 | 仅使用 Linear 时 | 目标项目 `.mcp.json` |
| `CLAUDE_PLUGIN_ROOT` | Hook 脚本路径解析 | 是 | Claude Code 自动设置 |
| `PYTHONIOENCODING` | Python 输出编码（设为 utf-8） | 推荐 | session-catchup.py 自动尝试设置 |

---

*集成分析: 2026-06-14*
