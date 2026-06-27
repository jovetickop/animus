---
description: 前端项目任务规划补充指南，适合处理 React/Vue 组件拆分、状态管理、样式处理等场景。
---

# 前端项目任务规划补充指南

<!-- 通用规划规则参见 agents/universal/feature-planner.md -->

## 前端项目识别

项目具备以下特征时，判定为前端项目：

- 存在 `package.json` 文件，且包含 `react` 或 `vue` 依赖
- 存在 `src/` 目录存放组件代码
- 使用 webpack/vite/esbuild 等打包工具
- 前端代码与后端代码在不同目录（常见结构：`frontend/` 或 `client/`）

## 前端任务规划原则

### 1. 技术栈感知

任务规划必须考虑前端框架特性：

| 框架 | 状态管理 | UI 库 | 构建工具 |
|------|---------|------|---------|
| React | Redux/Zustand/Recoil | Ant Design/Material UI | Vite/Create React App |
| Vue 2/3 | Pinia/Vuex | Element UI/Naive UI | Vite |
| 通用 | - | - | 原生 JS/CSS |

### 2. 组件粒度划分

前端任务应按组件粒度划分：

- **原子组件**：按钮、输入框、图标等最小单元
- **分子组件**：表单、卡片、列表等组合单元
- **页面组件**：完整页面，按业务功能划分
- **工具模块**：工具函数、hooks、状态管理

### 3. 任务类型识别

前端项目常见任务类型：

- **UI 组件开发**：新增/修改视觉组件
- **交互逻辑开发**：用户操作响应、表单验证
- **状态管理开发**：全局状态、API 数据同步
- **样式调整**：CSS/SCSS/Less 修改，响应式适配
- **性能优化**：懒加载、代码分割、缓存策略
- **集成对接**：API 对接、WebSocket、第三方 SDK

### 4. 测试策略

前端项目测试命令示例：

```json
{
  "react": "cd frontend && npm run build && npm run test",
  "vue": "cd frontend && npm run build && npm run test:unit",
  "vite": "cd frontend && npm run build && npm run lint"
}
```

前端任务必须包含 `build` 命令验证，确保代码可编译。

### 5. 依赖关系管理

前端任务依赖判断规则：

- 组件开发任务通常依赖 UI 库/设计系统任务
- 页面任务依赖基础组件任务
- 状态管理任务可能与后端 API 任务并行（接口定义后即可开始）
- 构建/部署任务依赖所有功能任务

### 6. 验收标准特殊考虑

前端验收标准应包含：

- **视觉验收**：组件渲染正确，样式符合设计稿
- **交互验收**：用户操作响应符合预期
- **兼容性验收**：主流浏览器兼容性（Chrome/Firefox/Safari/Edge）
- **性能验收**：首屏加载时间、交互响应时间

### 7. 特殊场景处理

#### SSR/SSG 项目（如 Next.js/Nuxt）

- 增加服务器端渲染测试
- 检查 SEO 相关功能（meta 标签、结构化数据）
- 验证静态资源生成

#### 包含子项目的 Monorepo

- 前端任务应明确指定工作目录（如 `cd frontend/`）
- 构建任务需考虑整个仓库的依赖关系
- 测试任务应分别在子项目目录执行

#### Electron/Tauri 桌面应用

- 增加打包验证步骤
- 检查原生模块集成
- 验证多平台构建（Windows/macOS/Linux）

## 前端任务规划示例

假设任务：将棋盘组件改版，需要支持自定义主题色

```json
{
  "id": "frontend-board-theming",
  "name": "前端棋盘主题支持",
  "description": "为棋盘组件添加主题切换功能，支持亮色/暗色模式",
  "status": "pending",
  "depends_on": ["frontend-state-management"],
  "priority": 85,
  "test_command": "cd frontend && npm run build && npm run test:unit -- --grep=Board",
  "acceptance_criteria": [
    "亮色模式显示正常",
    "暗色模式显示正常",
    "主题切换动画流畅",
    "切换后棋盘状态保持",
    "移动端适配正确"
  ]
}
```

## 风险与注意事项

1. **样式冲突**：多个人修改同一组件可能导致样式冲突，需要明确分工
2. **依赖版本**：前端依赖更新频繁，注意锁定版本避免破坏性变更
3. **浏览器兼容**：必要时添加 polyfill 或回退方案
4. **构建失败**：前端构建失败可能影响后续集成测试，应优先修复

## 验证要求

- 不得标记任务为 passed 之前跳过验证
- 必须执行 verify_command 并确认 exit 0
- 将验证输出写入 claude-progress.txt（至少最后3行）
- 不得修改 verify_config 中的 verify_command
- 生成的任务需包含 acceptance_criteria
