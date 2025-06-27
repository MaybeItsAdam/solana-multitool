import time
import random
from threading import Lock
from typing import Optional, Union, Any, Tuple, Callable, Type

class RateLimiter:
    """
    Token bucket rate limiter for API requests.
    
    Implements a token bucket algorithm to limit the rate of API calls,
    preventing rate limit violations and ensuring smooth operation.
    
    Attributes:
        max_requests: Maximum number of requests allowed per time window
        time_window: Time window in seconds (typically 1.0 for per-second limiting)
        tokens: Current number of available tokens
        last_update: Timestamp of last token update
        lock: Threading lock for thread-safe operations
    """
    
    def __init__(self, max_requests: int, time_window: float = 1.0):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per time window
            time_window: Time window in seconds (default: 1.0 second)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_update = time.time()
        self.lock = Lock()

    def acquire(self) -> None:
        """
        Acquire a token for making a request.
        
        Blocks if no tokens are available, implementing automatic rate limiting.
        This method is thread-safe and can be called from multiple threads.
        """
        with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            
            # Refill tokens based on time passed
            self.tokens = min(
                self.max_requests, 
                self.tokens + time_passed * (self.max_requests / self.time_window)
            )
            self.last_update = now

            if self.tokens < 1:
                # Not enough tokens, sleep until we have one
                sleep_time = (1 - self.tokens) * (self.time_window / self.max_requests)
                time.sleep(sleep_time)
                self.tokens = 0
            else:
                # Consume one token
                self.tokens -= 1

    def check_available(self) -> bool:
        """
        Check if tokens are available without consuming one.
        
        Returns:
            True if at least one token is available, False otherwise
        """
        with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            current_tokens = min(
                self.max_requests,
                self.tokens + time_passed * (self.max_requests / self.time_window)
            )
            return current_tokens >= 1

    def get_wait_time(self) -> float:
        """
        Get the estimated wait time until next token is available.
        
        Returns:
            Wait time in seconds (0 if tokens are immediately available)
        """
        with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            current_tokens = min(
                self.max_requests,
                self.tokens + time_passed * (self.max_requests / self.time_window)
            )
            
            if current_tokens >= 1:
                return 0.0
            else:
                return (1 - current_tokens) * (self.time_window / self.max_requests)

def exponential_backoff_sleep(retries: int, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True) -> None:
    """
    Sleep with exponential backoff for retry mechanisms.
    
    Implements exponential backoff with optional jitter to avoid thundering herd problems.
    Common pattern for handling rate limits, network errors, and API failures.
    
    Args:
        retries: Number of retries attempted (0-based)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        jitter: Whether to add random jitter (default: True)
    
    Example:
        for attempt in range(max_retries):
            try:
                result = make_api_call()
                break
            except RateLimitError:
                if attempt < max_retries - 1:
                    exponential_backoff_sleep(attempt)
    """
    # Calculate exponential delay: base_delay * (2 ^ retries)
    delay = min(base_delay * (2 ** retries), max_delay)
    
    # Add jitter to avoid thundering herd
    if jitter:
        # Add random jitter of ±25% of the delay
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(0.1, delay)  # Ensure minimum delay
    
    time.sleep(delay)

def linear_backoff_sleep(retries: int, base_delay: float = 1.0, max_delay: float = 10.0) -> None:
    """
    Sleep with linear backoff for retry mechanisms.
    
    Alternative to exponential backoff for cases where you want more gradual increase.
    
    Args:
        retries: Number of retries attempted (0-based)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 10.0)
    """
    delay = min(base_delay * (retries + 1), max_delay)
    time.sleep(delay)

def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    backoff_strategy: str = "exponential",
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Any:
    """
    Execute a function with automatic retry and backoff.
    
    Decorator-like function that handles retries with configurable backoff strategy.
    
    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        backoff_strategy: "exponential" or "linear"
        base_delay: Base delay for backoff
        max_delay: Maximum delay for backoff
        exceptions: Tuple of exceptions that trigger retries
    
    Returns:
        Result of successful function execution
    
    Raises:
        Last exception encountered if all retries fail
    
    Example:
        def unreliable_api_call():
            response = requests.get("https://api.example.com/data")
            response.raise_for_status()
            return response.json()
        
        result = retry_with_backoff(
            unreliable_api_call,
            max_retries=5,
            exceptions=(requests.RequestException,)
        )
    """
    last_exception: Optional[Exception] = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            
            # Don't sleep after the last attempt
            if attempt < max_retries:
                if backoff_strategy == "exponential":
                    exponential_backoff_sleep(attempt, base_delay, max_delay)
                elif backoff_strategy == "linear":
                    linear_backoff_sleep(attempt, base_delay, max_delay)
                else:
                    time.sleep(base_delay)
    
    # All retries failed, raise the last exception
    if last_exception is not None:
        raise last_exception
    else:
        # This should not happen in normal circumstances, but handle it gracefully
        raise RuntimeError(f"Function {func.__name__} failed after {max_retries} retries with no matching exceptions")

class RequestTracker:
    """
    Track API request statistics and performance.
    
    Useful for monitoring API usage, identifying bottlenecks, and debugging
    rate limiting issues.
    """
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_wait_time = 0.0
        self.start_time = time.time()
        self.lock = Lock()
    
    def record_request(self, success: bool, wait_time: float = 0.0) -> None:
        """
        Record a request attempt.
        
        Args:
            success: Whether the request was successful
            wait_time: Time spent waiting due to rate limiting
        """
        with self.lock:
            self.total_requests += 1
            if success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
            self.total_wait_time += wait_time
    
    def get_stats(self) -> dict:
        """
        Get current request statistics.
        
        Returns:
            Dictionary with request statistics
        """
        with self.lock:
            elapsed_time = time.time() - self.start_time
            return {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate": self.successful_requests / max(1, self.total_requests) * 100,
                "total_wait_time": self.total_wait_time,
                "avg_wait_time": self.total_wait_time / max(1, self.total_requests),
                "requests_per_second": self.total_requests / max(0.1, elapsed_time),
                "elapsed_time": elapsed_time
            }
    
    def print_stats(self) -> None:
        """Print formatted request statistics."""
        stats = self.get_stats()
        print("📊 Request Statistics:")
        print(f"   Total Requests: {stats['total_requests']}")
        print(f"   Successful: {stats['successful_requests']} ({stats['success_rate']:.1f}%)")
        print(f"   Failed: {stats['failed_requests']}")
        print(f"   Avg Wait Time: {stats['avg_wait_time']:.2f}s")
        print(f"   Requests/Second: {stats['requests_per_second']:.2f}")
        print(f"   Total Runtime: {stats['elapsed_time']:.1f}s")

# Convenience function for common use case
def create_rate_limiter(requests_per_second: int) -> RateLimiter:
    """
    Create a rate limiter for the specified requests per second.
    
    Args:
        requests_per_second: Maximum requests allowed per second
    
    Returns:
        Configured RateLimiter instance
    """
    return RateLimiter(max_requests=requests_per_second, time_window=1.0)

# Example usage and testing
if __name__ == "__main__":
    print("🧪 Testing network utilities...")
    
    # Test rate limiter
    print("\n📊 Testing RateLimiter (5 req/sec)...")
    limiter = create_rate_limiter(5)
    
    start_time = time.time()
    for i in range(10):
        limiter.acquire()
        print(f"   Request {i+1} at {time.time() - start_time:.2f}s")
    
    # Test exponential backoff
    print("\n⏰ Testing exponential backoff...")
    for retry in range(4):
        print(f"   Retry {retry}: sleeping...", end=" ")
        start = time.time()
        exponential_backoff_sleep(retry, base_delay=0.1, max_delay=2.0)
        print(f"{time.time() - start:.2f}s")
    
    # Test request tracker
    print("\n📈 Testing RequestTracker...")
    tracker = RequestTracker()
    
    # Simulate some requests
    for i in range(10):
        success = i % 3 != 0  # 2/3 success rate
        wait_time = random.uniform(0, 0.5)
        tracker.record_request(success, wait_time)
    
    tracker.print_stats()
    
    print("\n✅ Network utilities test completed!")