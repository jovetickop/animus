# 优化任务 ⑨：三层定制与团队配置

> 对应路线图：Phase 0 — 基础设施（重编号后对应 ⑨）
> 解决：所有行为硬编码，用户想调整必须 fork 插件

---

## 一、更改原因

### 1.1 当前问题

- 所有 agent 行为、审查严格度、规则全部硬编码在 md 文件中
- 用户想跳过命名检查或放松审查标准，必须 fork 插件
- 插件升级后 fork 的修改需要手动 merge
- 没有集中配置入口

### 1.2 解决后的效果

- 一个配置文件 `.claude/animus/config.toml` 控制全部行为
- git 跟踪，团队共享
- 不需要 fork 插件，改配置就行

---

## 二、更改方案

### 2.1 配置文件位置

```
.claude/animus/config.toml
```

放在 `.claude/animus/` 下，与 features.json、memlog 同目录，保持一致。

### 2.2 完整配置项

```toml
[dev]
# 默认行为路径：AI 自动检测时的倾向
default_path = "auto"         # auto / fast / light / full / oneshot
# 自主模式：true 时 AI 全权决策，不询问用户
autonomous = false

[review]
# 审查严格度
strictness = "normal"         # low / normal / high
# 跳过的审查类别
skip_categories = []          # 可选: naming, formatting, performance, security
# 每次审查最多输出多少条问题
max_findings = 20

[gates]
# 写代码前必须要有 in_progress 任务
require_task_before_write = true

[ponytail]
# 启用精简审查
enabled = true
# 文件超过此行数建议拆分
max_lines_per_file = 500

[party_mode]
# 默认运行模式
default_mode = "subagent"     # session / subagent / auto / agent-team
# 默认模板 ID
default_party = "arch-review" # arch-review / code-review
# 自动触发场景
auto_trigger = ["dev-full", "review-controversial"]
# 触发前是否询问用户
ask_before_start = true
# 最大辩论轮数
max_rounds = 3
# 持久记忆
memory_enabled = true

# 自定义角色（扩展默认模板）
[[party_mode.custom_members]]
code = "ui-reviewer"
name = "UI 审查官"
icon = "🎨"
title = "前端可用性审查"
persona = "关注界面可用性和用户体验……"

# 自定义模板
[[party_mode.custom_groups]]
id = "my-team"
name = "我的团队"
members = ["architect", "reviewer", "ui-reviewer"]
scene = "针对 UI 改动进行评审……"
```

### 2.3 三层覆盖规则

配置文件按以下层次叠加：

| 层 | 位置 | 优先级 | 谁修改 | git 跟踪 |
|----|------|--------|--------|---------|
| defaults | 插件内置（硬编码默认值） | 最低 | 插件作者 | 插件仓库 |
| team | `.claude/animus/config.toml` | 中 | 团队 | ✅ |
| user | `.claude/animus/config.user.toml` | 最高 | 个人用户 | ❌（gitignored） |

**合并规则：** team 层覆盖 defaults，user 层覆盖 team 层。文件不存在时回退到上一层默认值。

```python
def load_config():
    config = DEFAULT_CONFIG  # 硬编码默认值
    team_path = ".claude/animus/config.toml"
    user_path = ".claude/animus/config.user.toml"
    
    if os.path.exists(team_path):
        team_cfg = tomllib.load(open(team_path, "rb"))
        deep_merge(config, team_cfg)  # team 覆盖 defaults
    
    if os.path.exists(user_path):
        user_cfg = tomllib.load(open(user_path, "rb"))
        deep_merge(config, user_cfg)  # user 覆盖 team
    
    return config
```### 2.3 配置读取方式

每个命令/agent 启动时从 `.claude/animus/config.toml` 读取配置。

如果文件不存在，使用默认值（硬编码在 md 中的当前行为）。

```python
def load_config():
    path = ".claude/animus/config.toml"
    if not os.path.exists(path):
        return DEFAULT_CONFIG
    return tomllib.load(open(path, "rb"))  # Python 3.11+
```

### 2.5 默认配置

新建 `config.toml` 时写入默认值，所有项带注释说明：

```toml
# animus 团队配置文件
# 在项目根目录 .claude/animus/config.toml
# git 跟踪，团队共享

[dev]
default_path = "auto"
autonomous = false

[review]
strictness = "normal"
skip_categories = []
max_findings = 20

[gates]
require_task_before_write = true

[ponytail]
enabled = true
max_lines_per_file = 500

[party_mode]
default_mode = "subagent"
default_party = "arch-review"
auto_trigger = ["dev-full", "review-controversial"]
ask_before_start = true
max_rounds = 3
memory_enabled = true
```

### 2.6 改动文件

| 文件 | 改动 |
|------|------|
| 新建 `.claude/animus/config.toml` | 团队配置（git 跟踪） |
| 新建 `.claude/animus/config.user.toml` | 用户配置（gitignored） |
| 新建 `commands/animus-config.md` | 管理配置文件 |
| 所有命令/agent 文件 | 启动时读取配置覆盖默认行为 |

## 三、架构影响评估

| 维度 | 评估 |
|------|------|
| 性能 | 启动时单次读文件，无运行时影响 |
| 兼容性 | 文件不存在时完全回退到当前硬编码行为，零破坏 |
| 降级 | 任一配置文件损坏/不存在 → 回退到上一层默认值，不 crash |

## 四、验证方法

1. 确认 `.claude/animus/config.toml` 存在且有默认值
2. 修改 `review.strictness = "low"` → 确认审查输出变少
3. 修改 `ponytail.enabled = false` → 确认 ponytail-reviewer 跳过
4. 在 `config.user.toml` 中覆盖一个值 → 确认 user 层优先级高于 team 层
5. 删除配置文件 → 确认回退到默认行为
6. 确认 `config.user.toml` 在 .gitignore 中
