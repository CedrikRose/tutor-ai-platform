"""Retry logic and circuit breaker for resilient API calls."""
import asyncio
import time
import random
from typing import Callable, Any, Tuple, Type
from enum import Enum
import logging

from config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Too many failures, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class BedrockCircuitBreaker:
    """
    Circuit breaker pattern to handle cascading AWS rate limit failures.

    Prevents overwhelming the service when it's already struggling.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 300.0,
        name: str = "bedrock"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # Time to wait before attempting recovery
        self.name = name

        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.open_time = None
        self.last_failure_time = None

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.state != CircuitState.OPEN:
            return False

        if self.open_time is None:
            return False

        return time.time() - self.open_time >= self.timeout

    def record_success(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}': recovered, moving to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.open_time = None

    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            if self.state == CircuitState.CLOSED:
                logger.warning(
                    f"Circuit breaker '{self.name}': threshold reached "
                    f"({self.failure_count} failures), moving to OPEN"
                )
                self.state = CircuitState.OPEN
                self.open_time = time.time()
            elif self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker '{self.name}': test failed, back to OPEN")
                self.state = CircuitState.OPEN
                self.open_time = time.time()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Raises:
            CircuitBreakerOpen: If circuit is open and timeout not elapsed
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}': attempting recovery (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
            else:
                time_remaining = self.timeout - (time.time() - self.open_time)
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry in {time_remaining:.1f}s"
                )

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


async def call_with_exponential_backoff(
    func: Callable,
    max_attempts: int = None,
    base_delay: float = None,
    max_delay: float = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    circuit_breaker: BedrockCircuitBreaker = None
) -> Any:
    """
    Call function with exponential backoff and jitter.

    Args:
        func: Function to call (can be sync or async)
        max_attempts: Maximum retry attempts (default from settings)
        base_delay: Base delay in seconds (default from settings)
        max_delay: Maximum delay in seconds (default from settings)
        exceptions: Tuple of exceptions to catch and retry
        circuit_breaker: Optional circuit breaker to use

    Returns:
        Function result

    Raises:
        Last exception if all attempts fail
    """
    if max_attempts is None:
        max_attempts = settings.retry_max_attempts
    if base_delay is None:
        base_delay = settings.retry_base_delay
    if max_delay is None:
        max_delay = settings.retry_max_delay

    last_exception = None

    for attempt in range(max_attempts):
        try:
            # Call through circuit breaker if provided
            if circuit_breaker:
                return await circuit_breaker.call(func)
            else:
                return await func() if asyncio.iscoroutinefunction(func) else func()

        except CircuitBreakerOpen as e:
            logger.warning(f"Circuit breaker open: {e}")
            # Don't count as retry attempt, just wait
            await asyncio.sleep(30)
            continue

        except exceptions as e:
            last_exception = e
            attempt_num = attempt + 1

            if attempt_num >= max_attempts:
                logger.error(f"Max attempts ({max_attempts}) reached: {e}")
                break

            # Calculate delay with exponential backoff and jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            # Add jitter: multiply by random factor between 0.5 and 1.0
            jittered_delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                f"Attempt {attempt_num}/{max_attempts} failed: {e.__class__.__name__}: {e}. "
                f"Retrying in {jittered_delay:.2f}s..."
            )

            await asyncio.sleep(jittered_delay)

    # All attempts failed
    raise last_exception


def is_throttling_error(exception: Exception) -> bool:
    """Check if exception is a throttling/rate limit error."""
    error_str = str(exception).lower()
    error_type = exception.__class__.__name__.lower()

    throttling_indicators = [
        'throttling',
        'rate limit',
        'too many requests',
        'quota exceeded',
        '429',
        'servicequotaexceeded'
    ]

    return any(indicator in error_str or indicator in error_type for indicator in throttling_indicators)


def should_retry(exception: Exception) -> bool:
    """Determine if exception is retryable."""
    # Always retry throttling errors
    if is_throttling_error(exception):
        return True

    # Retry on common transient errors
    retryable_patterns = [
        'timeout',
        'connection',
        'network',
        'temporarily unavailable',
        'service unavailable',
        '500',
        '502',
        '503',
        '504'
    ]

    error_str = str(exception).lower()
    return any(pattern in error_str for pattern in retryable_patterns)
