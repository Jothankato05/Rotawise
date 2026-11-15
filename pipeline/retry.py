"""Retry with exponential backoff and jitter for flaky remote calls."""

from __future__ import annotations

import logging
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")
log = logging.getLogger("rotawise.pipeline")


def with_retry(fn: Callable[[], T], *, what: str, attempts: int = 5, base: float = 2.0, cap: float = 60.0) -> T:
    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - remote APIs raise many types
            last = exc
            if i == attempts:
                break
            delay = min(cap, base ** i) * (0.5 + random.random() / 2)
            log.warning("%s failed (attempt %d/%d): %s; retrying in %.1fs", what, i, attempts, exc, delay)
            time.sleep(delay)
    raise RuntimeError(f"{what} failed after {attempts} attempts") from last
