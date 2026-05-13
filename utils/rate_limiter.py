import time
import threading
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._attempts[key]
            timestamps[:] = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self.max_attempts:
                return False
            timestamps.append(now)
            return True

    def remaining(self, key: str) -> int:
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._attempts[key]
            timestamps[:] = [t for t in timestamps if t > cutoff]
            return max(0, self.max_attempts - len(timestamps))

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

login_limiter = RateLimiter(max_attempts=10, window_seconds=60)
register_limiter = RateLimiter(max_attempts=3, window_seconds=300)
