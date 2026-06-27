# Go 编码最佳实践

## Go 版本选择

- 新项目默认使用 Go 1.21+，利用泛型和新标准库特性。
- 存量项目保持版本一致，升级前确认 go.mod go 版本兼容。
- go.mod 中显式声明 go 版本，使用 `go mod tidy` 保持依赖整洁。

## gofmt 与代码风格

- 所有代码必须通过 `gofmt` 或 `go fmt` 格式化，禁止手动对齐。
- 使用 `go vet` 进行静态检查，提交前确保无警告。
- 编辑器配置保存时自动运行 gofmt。

## 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| 包名 | 全小写，简短无下划线 | `httputil` |
| 变量/函数 | camelCase（首字母大小写控制可见性） | `currentIndex`, `ParseConfig` |
| 类型/接口 | PascalCase | `UserService` |
| 常量 | PascalCase | `MaxRetryCount` |
| 文件命名 | snake_case | `user_service.go` |
| 测试文件 | `*_test.go` | `user_service_test.go` |

## 错误处理规范

- 使用 `error` 返回值而非 panic。库代码禁止 panic，顶层 main 可酌情处理。
- 使用 `fmt.Errorf` 或 `errors.New` 创建错误，使用 `errors.Is`/`errors.As` 判断错误链。
- 不要在函数签名中省略错误返回值。
- 成功路径优先处理，错误路径延迟处理。
- 使用 `defer` 确保资源释放和锁释放。

## 依赖管理规范

- 使用 `go mod init` 初始化模块，`go mod tidy` 整理依赖。
- go.mod 和 go.sum 必须纳入版本控制。
- 引入新依赖前评估维护活跃度和依赖树膨胀。
- 避免使用 `replace` 指令覆盖依赖，除非临时开发需要。

## 并发模式规范

- goroutine 必须明确生命周期和退出路径（使用 channel 或 context 通知退出）。
- 使用 `sync.WaitGroup` 等待 goroutine 组完成。
- 使用 `sync.Mutex`/`sync.RWMutex` 保护共享数据，优先考虑 channel 通信。
- 使用 `context.Context` 传递取消信号和超时。
- 使用 `go test -race` 检测数据竞争。
- 限制 goroutine 数量，避免无限制创建导致资源耗尽。

## 测试规范

- 每个包必须有对应的 `*_test.go` 测试文件。
- 优先使用 table-driven tests 组织测试用例。
- 测试函数命名：`TestXxx`（单元测试）、`BenchmarkXxx`（基准测试）、`ExampleXxx`（示例测试）。
- 使用 `go test -cover` 检查测试覆盖率。
- 使用 `go test -race` 检测数据竞争。
- 基准测试使用 `go test -bench=.` 运行。

## 提交前检查清单

- [ ] 代码已通过 `go fmt` 格式化
- [ ] `go vet` 无警告
- [ ] `go test` 全部通过
- [ ] 新行为有对应测试
- [ ] 无 goroutine 泄露风险
- [ ] 错误处理完整（无忽略的错误返回值）
- [ ] 构建通过
