# Node/TypeScript 最佳实践

## ESLint 与 Prettier

- ESLint 配置使用 `@typescript-eslint` 规则集，Prettier 负责格式化，避免规则冲突。
- 提交前启用 lint-staged + husky 自动检查暂存文件。
- CI 中加入 `lint` 步骤，阻止未通过 lint 的代码合入。

## 包管理

- 锁定依赖版本：npm 使用 `package-lock.json`，yarn 使用 `yarn.lock`，pnpm 使用 `pnpm-lock.yaml`。
- 定期运行 `npm audit` 或 `pnpm audit` 检查安全漏洞。
- 避免混用不同包管理器，统一使用项目声明的工具。

## 命名约定

- 变量/函数/文件：`camelCase`（如 `fetchUserData.ts`）
- 类/组件/类型/接口：`PascalCase`（如 `UserProfile.tsx`）
- 常量：`UPPER_SNAKE_CASE`（如 `MAX_RETRY_COUNT`）
- 目录名：小写 kebab-case（如 `user-profile/`）

## 构建工具链

- 前端默认 Vite，传统项目可继续使用 Webpack。
- 库/工具包优先使用 tsup 或 esbuild 打包。
- TypeScript 编译目标根据项目兼容需求设定（如 `ES2020`）。

## 安全规范

- 用户输入必须校验和转义，防止 XSS 与注入攻击。
- 敏感信息（密钥、令牌）使用环境变量，不硬编码在源码中。
- 后端接口实施限流与鉴权，不信任客户端传来的任何数据。
- 定期更新依赖，重点关注 `npm audit` 的 `critical` 和 `high` 级别问题。
