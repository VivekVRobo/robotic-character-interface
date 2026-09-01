"""Clock helpers separating audit time from freshness time."""

from datetime import UTC, datetime
from time import monotonic_ns


def utc_now() -> datetime:
    """Return timezone-aware wall-clock time for audit/history records."""
    return datetime.now(UTC)


def monotonic_now_ns() -> int:
    """Return monotonic time for TTL, watchdog, and latency calculations."""
    return monotonic_ns()


def age_ms(since_ns: int, *, now_ns: int | None = None) -> float:
    """Return elapsed milliseconds; negative values expose invalid future timestamps."""
    current = monotonic_now_ns() if now_ns is None else now_ns
    return (current - since_ns) / 1_000_000.0
