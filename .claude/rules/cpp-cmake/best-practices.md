# C++/CMake 编码最佳实践

## C++ 标准选择

- 新项目默认使用 **C++17**，老旧项目逐步从 C++11/14 迁移。
- 需要 `concepts`、`ranges`、`coroutines` 等特性的项目使用 C++20。
- 在 `CMakeLists.txt` 中显式声明：`set(CMAKE_CXX_STANDARD 17)` 并 `set(CMAKE_CXX_STANDARD_REQUIRED ON)`。

## CMake 配置规范

- 使用 `cmake_minimum_required(VERSION 3.21)` 或更高版本。
- 启用 `CMAKE_EXPORT_COMPILE_COMMANDS` 方便静态分析。
- 使用 `target_include_directories`、`target_link_libraries` 替代全局设置。
- 使用 `FetchContent` 管理第三方依赖，避免手动复制源码。
- 用 `option()` 定义可配置开关（如 `BUILD_TESTS`、`ENABLE_SANITIZERS`）。

## 编译器与警告

- MSVC：`/W4` 或 `/W4 /permissive-`；GCC/Clang：`-Wall -Wextra -Wpedantic`。
- 启用 sanitizers 调试：`-fsanitize=address,undefined`。
- 不要过度压制警告，不要全局使用 `-w` 或 `/W0`。

## 现代 C++ 特性推荐

- 优先使用 `std::unique_ptr` 管理独占所有权，`std::shared_ptr` 仅用于共享所有权。
- 使用 `constexpr` 优化编译期计算。
- 使用 `std::optional` 表达"可能有值"，`std::variant` 表达"多种类型之一"。
- 使用 `auto` 推导显而易见类型，避免过度使用导致代码可读性下降。
- 优先使用 `std::array` 替代 C 风格定长数组。
- 避免手动 `new`/`delete`，使用 RAII 管理资源。

## 构建与测试

- 启用 `CTest` 管理测试注册。
- 测试框架推荐 GoogleTest（可考虑 QtTest 仅在 Qt 项目中使用）。
- 在 `CMakeLists.txt` 中使用 `enable_testing()` + `add_test()` 注册测试。
