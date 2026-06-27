---
name: tdd-workflow
description: 面向通用 C++/Qt 开发的 TDD 工作流指南，使用 /tdd-workflow 显式调用
---
# C++/Qt 测试驱动开发 (TDD) 工作流

此 skill 用于约束通用 C++/Qt 项目的功能开发、缺陷修复与重构过程，确保改动以测试为先，并且可以通过 CMake/CTest 持续验证。

## 如何使用

**显式调用**: 输入 `/tdd-workflow` 激活此工作流

## 适用场景

- 新增类、模块或业务能力
- 修复缺陷或回归问题
- 重构已有实现
- 调整 Qt Widgets、QML 或 Qt Core 逻辑
- 修改信号槽、线程、定时器、文件读写、网络、数据库等行为
- 补齐已有功能的自动化测试

## 核心原则

### 1. 先写失败测试，再写实现

任何非纯文档改动，默认先定义可执行的验证方式。优先顺序如下：

1. 单元测试
2. 集成测试
3. UI smoke test
4. 手工验证（仅在无法自动化时作为补充）

### 2. 先验证行为，再关注实现细节

- 优先测试输入、输出、状态变化、信号发射、副作用和错误处理。
- 不要把测试绑死在私有实现细节上。
- 不要为了让测试方便而破坏类职责或接口设计。

### 3. 让测试可重复、可定位、可维护

- 每个测试覆盖一个明确行为。
- 测试命名要能说明前提、动作和期望结果。
- 测试失败后应能快速定位是输入问题、状态问题还是时序问题。

### 4. C++/Qt 项目要同时关注语言层和框架层风险

- C++ 层面：资源管理、边界条件、异常安全、值语义/引用语义、并发访问。
- Qt 层面：`QObject` 所有权、信号槽连接、事件循环、线程亲和性、异步回调、UI 响应性。

## 测试类型选择

### 1. 纯 C++ 逻辑

适用于算法、数据结构、解析器、规则引擎、工具函数等无 Qt 依赖的代码。

- 推荐：`GoogleTest`
- 重点覆盖：
  - 正常输入
  - 空输入
  - 无效输入
  - 边界值
  - 回归样例

### 2. Qt Core / 非 UI 逻辑

适用于 `QObject`、信号槽、`QTimer`、文件系统、网络封装、模型层、配置读写等。

- 推荐：`QTest` 或 `GoogleTest + Qt event loop`
- 重点覆盖：
  - 信号是否按预期发射
  - 异步流程是否能在超时内完成
  - 状态切换是否正确
  - 线程切换是否安全

### 3. Qt UI 逻辑

适用于 `QWidget`、对话框、主窗口、QML 交互层等。

- 优先测：
  - 默认状态
  - 用户动作后的状态变化
  - 关键控件可用性
  - 基本 smoke 流程
- 不要把像素级渲染截图比对作为默认方案。
- 不要把纯手工点击当作唯一验证方式。

## TDD 工作流步骤

### 第 1 步：明确需求与验收标准

先把需求收敛成可验证语句：

```text
功能: [功能名称]
输入: [输入条件]
行为: [系统执行的动作]
结果: [可观测结果]
异常: [失败或边界场景]
```

示例：

```text
功能: 配置文件加载
输入: 给定一个存在且格式正确的 json 配置文件
行为: ConfigLoader 读取并解析文件
结果: 返回解析后的配置对象
异常: 文件不存在或格式错误时返回失败并给出错误信息
```

### 第 2 步：先写测试用例

根据验收标准先写失败测试。

`GoogleTest` 示例：

```cpp
#include <gtest/gtest.h>
#include "config_loader.h"

TEST(ConfigLoaderTest, LoadsValidJsonFile) {
    ConfigLoader loader;

    auto result = loader.load(":/testdata/valid_config.json");

    ASSERT_TRUE(result.ok());
    EXPECT_EQ(result.value().windowTitle, "Demo");
}

TEST(ConfigLoaderTest, ReturnsErrorWhenFileDoesNotExist) {
    ConfigLoader loader;

    auto result = loader.load("missing.json");

    ASSERT_FALSE(result.ok());
    EXPECT_EQ(result.error(), ConfigError::FileNotFound);
}
```

`QTest` 示例：

```cpp
#include <QtTest>
#include "task_runner.h"

class TaskRunnerTest : public QObject {
    Q_OBJECT

private slots:
    void emitsFinishedAfterRun();
};

void TaskRunnerTest::emitsFinishedAfterRun()
{
    TaskRunner runner;
    QSignalSpy finishedSpy(&runner, &TaskRunner::finished);

    runner.start();

    QTRY_COMPARE(finishedSpy.count(), 1);
}

QTEST_MAIN(TaskRunnerTest)
#include "task_runner_test.moc"
```

### 第 3 步：运行测试，确认失败

失败必须是“因为功能尚未实现”或“当前行为不满足需求”，而不是因为测试本身无效。

```bash
cmake -B build -DBUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

### 第 4 步：编写最小实现

只写足够让当前测试通过的实现，不顺手做无关扩展。

```cpp
Result<Config, ConfigError> ConfigLoader::load(const QString& path)
{
    QFile file(path);
    if (!file.exists()) {
        return Result<Config, ConfigError>::failure(ConfigError::FileNotFound);
    }

    // 先满足当前测试，后续再继续扩展解析逻辑。
    return parse(file);
}
```

### 第 5 步：再次运行测试

```bash
cmake --build build
ctest --test-dir build --output-on-failure
```

### 第 6 步：重构并保留绿色状态

在所有相关测试通过的前提下再做：

- 提取重复逻辑
- 改进命名
- 拆分类职责
- 优化资源管理
- 收敛 Qt 生命周期或线程模型

## 通用测试模式

### 1. 纯 C++ 类测试

```cpp
#include <gtest/gtest.h>
#include "range_validator.h"

TEST(RangeValidatorTest, AcceptsValueInsideRange) {
    RangeValidator validator(1, 10);

    EXPECT_TRUE(validator.isValid(5));
}

TEST(RangeValidatorTest, RejectsValueOutsideRange) {
    RangeValidator validator(1, 10);

    EXPECT_FALSE(validator.isValid(11));
}
```

### 2. `QObject` 与信号槽测试

```cpp
#include <QtTest>
#include "document_service.h"

class DocumentServiceTest : public QObject {
    Q_OBJECT

private slots:
    void emitsDocumentLoaded();
};

void DocumentServiceTest::emitsDocumentLoaded()
{
    DocumentService service;
    QSignalSpy spy(&service, &DocumentService::documentLoaded);

    service.load(":/testdata/demo.txt");

    QTRY_COMPARE(spy.count(), 1);
}
```

### 3. `QWidget` 状态测试

```cpp
#include <QtTest>
#include "settings_dialog.h"

class SettingsDialogTest : public QObject {
    Q_OBJECT

private slots:
    void disablesApplyButtonWhenInputInvalid();
};

void SettingsDialogTest::disablesApplyButtonWhenInputInvalid()
{
    SettingsDialog dialog;
    dialog.show();

    auto *lineEdit = dialog.findChild<QLineEdit*>("hostLineEdit");
    auto *applyButton = dialog.findChild<QPushButton*>("applyButton");

    QVERIFY(lineEdit != nullptr);
    QVERIFY(applyButton != nullptr);

    QTest::keyClicks(lineEdit, " ");
    QTRY_VERIFY(!applyButton->isEnabled());
}
```

### 4. 异步流程测试

```cpp
#include <QtTest>
#include "download_manager.h"

class DownloadManagerTest : public QObject {
    Q_OBJECT

private slots:
    void reportsFailureOnTimeout();
};

void DownloadManagerTest::reportsFailureOnTimeout()
{
    DownloadManager manager;
    QSignalSpy failedSpy(&manager, &DownloadManager::downloadFailed);

    manager.start("http://127.0.0.1:9/unreachable");

    QTRY_VERIFY_WITH_TIMEOUT(failedSpy.count() == 1, 3000);
}
```

## 测试文件组织建议

```text
tests/
├── CMakeLists.txt
├── unit/
│   ├── test_range_validator.cpp
│   └── test_config_loader.cpp
├── integration/
│   ├── test_document_service.cpp
│   └── test_repository_flow.cpp
└── ui/
    ├── test_settings_dialog.cpp
    └── test_mainwindow_smoke.cpp
```

命名建议：

- 纯 C++ 单元测试：`test_<module>.cpp`
- Qt 组件测试：`test_<class_or_feature>.cpp`
- UI smoke test：`test_<screen>_smoke.cpp`

## CMake 测试配置参考

```cmake
enable_testing()

find_package(GTest CONFIG REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Core Test Widgets)

add_executable(test_settings_dialog
    tests/ui/test_settings_dialog.cpp
    src/settings_dialog.cpp
)

target_link_libraries(test_settings_dialog
    PRIVATE
    GTest::gtest
    Qt6::Core
    Qt6::Test
    Qt6::Widgets
)

add_test(NAME test_settings_dialog COMMAND test_settings_dialog)
```

如果项目使用 Qt5、QTest-only 或已有自定义测试宏，应保持现有体系，不要为了“统一”而强行重构整个测试基础设施。

## Qt 开发中的重点风险

### 1. `QObject` 生命周期

- 优先依赖父子关系管理对象。
- 跨线程对象不要在错误线程直接销毁。
- 测试中不要制造悬空指针再把它当“边缘场景”。

### 2. 信号槽和事件循环

- 异步逻辑必须等待可观测结果，不要直接 `sleep` 代替事件驱动验证。
- 优先使用 `QSignalSpy`、`QTRY_VERIFY`、`QTRY_COMPARE`。

### 3. UI 测试边界

- 测试控件状态、文本、使能关系和关键交互流程。
- 不要过度依赖绝对坐标、像素尺寸和平台相关外观。

### 4. 线程与耗时任务

- 关注 UI 线程是否阻塞。
- 关注 worker 对象的线程亲和性是否正确。
- 对 timeout、取消、中断和错误回传写专门测试。

## 常见错误与正确做法

### ❌ 错误：跳过失败测试，直接写实现

```text
“这个功能很简单，先写完再补测试。”
```

### ✅ 正确：先定义失败用例

```text
先用 2 到 5 个最小测试锁定行为，再实现。
```

### ❌ 错误：测试私有实现细节

```cpp
EXPECT_EQ(service.internalBufferSize(), 3);
```

### ✅ 正确：测试外部可观察行为

```cpp
EXPECT_EQ(service.documents().size(), 3);
```

### ❌ 错误：用 `QThread::sleep()` 等待异步完成

```cpp
worker.start();
QThread::sleep(1);
EXPECT_TRUE(worker.isFinished());
```

### ✅ 正确：等待信号或状态变化

```cpp
worker.start();
QTRY_VERIFY(worker.isFinished());
```

### ❌ 错误：把手工点击当成唯一验证

```text
“我本地点过了，应该没问题。”
```

### ✅ 正确：至少补最小自动化验证

```text
为关键状态变化补 smoke test，手工验证只作为补充说明。
```

## 持续验证

开发期间至少反复执行：

```bash
cmake --build build
ctest --test-dir build --output-on-failure
```

必要时执行定向测试：

```bash
ctest --test-dir build -R "ConfigLoader|SettingsDialog" --output-on-failure
```

如果仓库启用了 harness，还应同步：

- 把验证命令写入 `.claude/harness/features.json`
- 把最新结果写入 `.claude/harness/claude-progress.txt`

## 完成标准

一个任务只有在以下条件都满足时，才算通过 TDD 闭环：

- 需求已转成可执行验收标准
- 失败测试先于实现出现
- 相关实现已使测试变绿
- 构建成功
- 相关测试可重复执行
- 已记录当前验证命令和结果

---

**记住**：TDD 的目标不是“测试越多越好”，而是让 C++/Qt 改动在重构、扩展和回归时始终有可靠的反馈。优先测试关键行为、生命周期边界、异步时序和用户可感知的状态变化。
