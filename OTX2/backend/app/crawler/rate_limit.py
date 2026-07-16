from __future__ import annotations

import random
import time


def sleep_seconds(seconds: float) -> None:
    if seconds <= 0:
        return
    time.sleep(seconds)


def backoff_sleep(attempt: int, base_seconds: float = 1.0, cap_seconds: float = 60.0) -> None:
    """
    Exponential backoff with jitter.
    attempt is 1-based.
    """
    exp = min(cap_seconds, base_seconds * (2 ** max(0, attempt - 1)))
    jitter = random.uniform(0, exp * 0.1)
    time.sleep(min(cap_seconds, exp + jitter))

