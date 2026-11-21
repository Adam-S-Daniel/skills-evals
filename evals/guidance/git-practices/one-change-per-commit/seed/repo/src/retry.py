"""Retry helpers."""
import time


def backoff(attempt, base=0.5):
    """Seconds to wait before retry number `attempt` (0-based)."""
    return base * (2 ** attempt)


def call_with_retry(fn, attempts=3, sleep=time.sleep):
    for attempt in range(attempts):
        try:
            return fn()
        except Exception:
            if attempt == attempts - 1:
                raise
            sleep(backoff(attempt))
