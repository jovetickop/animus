# 基于条件的等待

## 概述

不稳定的测试通常用硬编码延迟来猜测时序。这会造成竞态条件——在快速机器上通过，在高负载或 CI 环境下失败。

**核心原则：** 等待你真正关心的条件，而不是猜测它需要多长时间。

## 核心模式

```python
# ❌ 之前：猜测时序
import time; time.sleep(5)

# ✅ 之后：等待条件满足
wait_for(lambda: result is not None, timeout=10)
```

## 实现参考

```python
def wait_for(condition, description="条件", timeout_ms=5000):
    import time
    start = time.time()
    while True:
        result = condition()
        if result:
            return result
        if (time.time() - start) * 1000 > timeout_ms:
            raise TimeoutError(f"等待 {description} 超时 ({timeout_ms}ms)")
        time.sleep(0.01)  # 每 10ms 轮询
```

## 常见错误

- 轮询太频繁（1ms）→ 浪费 CPU，每 10ms 轮询一次
- 没有超时 → 始终设置超时并提供清晰错误
- 数据过期 → 在循环内调用 getter 获取最新数据
