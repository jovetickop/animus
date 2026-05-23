# 已有工程 Harness 说明

将 `templates/harness/` 下的文件复制到 `.claude/harness/` 后，需要继续适配：

- 构建命令
- 测试命令
- `features.json` 中的初始任务列表
- `claude-progress.txt` 中的项目特有说明

## 建议接入顺序

1. 先确认当前仓库的实际构建入口，例如 `cmake --build build` 或你们现有的脚本
2. 再确认测试入口，例如 `ctest --test-dir build --output-on-failure`
3. 用真实项目需求替换 `features.json` 中的示例任务
   - 建议同时补齐 `depends_on`、`priority`、`last_error`、`updated_at` 字段
4. 在 `claude-progress.txt` 里补一条初始化记录，说明当前仓库的接入背景
5. 首次编码前先运行一次 `show-status.py`，确认状态文件可读

## 接入后的最低要求

- Claude Code 能明确找到当前任务
- 每个任务都有可执行的验证命令
- 构建失败时能回写进度日志
- 每次状态流转后会自动生成/更新 `docs/reports/<任务编号>-任务描述.md`
- 现有源码目录、目标结构和 Qt 架构不被模板误改
