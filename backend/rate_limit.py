from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass
class RateLimiter:
    max_requests: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        ts = time.time() if now is None else now
        hits = self._hits.setdefault(key, [])
        cutoff = ts - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.pop(0)
        if len(hits) >= self.max_requests:
            return False
        hits.append(ts)
        return True
