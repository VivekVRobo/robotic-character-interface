from datetime import UTC

from rci.domain.timestamps import age_ms, utc_now


def test_utc_now_is_timezone_aware_utc() -> None:
    assert utc_now().tzinfo is UTC


def test_age_ms_uses_monotonic_nanoseconds() -> None:
    assert age_ms(1_000_000_000, now_ns=1_250_000_000) == 250.0


def test_age_ms_exposes_future_timestamp() -> None:
    assert age_ms(2_000_000_000, now_ns=1_000_000_000) == -1000.0
