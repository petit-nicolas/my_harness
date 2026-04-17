"""
指数退避重试模块

为 API 调用提供可配置的重试逻辑，自动处理：
- 429 Rate Limit（触发后等待更长时间）
- 5xx 服务器内部错误
- 网络连接超时

设计原则：
- with_retry() 是通用包装，接受任意可调用对象
- 重试等待时间 = base_delay * 2^attempt + 随机抖动（避免惊群）
- 最终仍失败时透传原始异常，便于上层处理
"""
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")

# 触发 429 时额外等待的倍率（速率限制比普通 5xx 需要更长冷却）
_RATE_LIMIT_EXTRA = 2.0


def _is_retryable(exc: Exception) -> bool:
    """判断异常是否值得重试"""
    try:
        from openai import RateLimitError, APIConnectionError, APIStatusError
        if isinstance(exc, RateLimitError):
            return True
        if isinstance(exc, APIConnectionError):
            return True
        if isinstance(exc, APIStatusError) and exc.status_code >= 500:
            return True
    except ImportError:
        pass
    return False


def _is_rate_limit(exc: Exception) -> bool:
    """是否是速率限制错误（需要额外等待）"""
    try:
        from openai import RateLimitError
        return isinstance(exc, RateLimitError)
    except ImportError:
        return False


def _backoff_seconds(attempt: int, base: float, rate_limited: bool) -> float:
    """
    计算本次等待时长。

    公式：base * 2^attempt + jitter
    rate_limited=True 时额外乘以倍率。
    """
    wait = base * (2 ** attempt) + random.uniform(0, 0.5)
    if rate_limited:
        wait *= _RATE_LIMIT_EXTRA
    return min(wait, 60.0)  # 单次等待上限 60s


def with_retry(
    fn: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> T:
    """
    带指数退避的重试包装器。

    Args:
        fn:           要重试的可调用对象（无参数）
        max_attempts: 最大尝试次数（含首次，默认 3）
        base_delay:   基础等待秒数（默认 1.0s）
        on_retry:     重试前触发的回调 (attempt_no, exc, wait_secs)
                      可用于日志 / UI 提示

    Returns:
        fn() 的返回值

    Raises:
        最后一次尝试失败的原始异常
    """
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            if not _is_retryable(exc):
                raise   # 非可重试错误（如 401/403）直接抛出

            last_exc = exc
            if attempt == max_attempts - 1:
                break   # 最后一次，不再等待

            wait = _backoff_seconds(attempt, base_delay, _is_rate_limit(exc))
            if on_retry:
                on_retry(attempt + 1, exc, wait)
            time.sleep(wait)

    raise last_exc  # type: ignore[misc]


def retry_error_type(exc: Exception) -> str:
    """返回可读的错误类型描述（供 UI 显示）"""
    try:
        from openai import RateLimitError, APIConnectionError, APIStatusError
        if isinstance(exc, RateLimitError):
            return "429 速率限制"
        if isinstance(exc, APIConnectionError):
            return "网络连接失败"
        if isinstance(exc, APIStatusError):
            return f"服务器错误 {exc.status_code}"
    except ImportError:
        pass
    return type(exc).__name__
