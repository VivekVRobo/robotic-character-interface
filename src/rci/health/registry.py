"""Health provider registry and aggregate evaluation."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass

from rci.domain.enums import HealthStatus
from rci.domain.timestamps import monotonic_now_ns, utc_now
from rci.health.checks import HealthProvider
from rci.health.models import ComponentHealth, HealthReport


@dataclass(frozen=True, slots=True)
class _ProviderRegistration:
    name: str
    provider: HealthProvider
    critical: bool


class HealthRegistry:
    """Own registered health providers and evaluate them concurrently."""

    def __init__(self) -> None:
        self._providers: dict[str, _ProviderRegistration] = {}

    def register(self, name: str, provider: HealthProvider, *, critical: bool = False) -> None:
        if not name:
            raise ValueError("health provider name cannot be empty")
        if name in self._providers:
            raise ValueError(f"health provider already registered: {name}")
        self._providers[name] = _ProviderRegistration(name, provider, critical)

    def unregister(self, name: str) -> bool:
        return self._providers.pop(name, None) is not None

    def names(self) -> tuple[str, ...]:
        return tuple(self._providers)

    async def check_all(self) -> HealthReport:
        registrations = tuple(self._providers.values())
        results = await asyncio.gather(
            *(self._check_one(registration) for registration in registrations)
        )
        components = {result.component: result for result in results}
        return HealthReport(
            overall=aggregate_health(components.values()),
            components=components,
            checked_at=utc_now(),
        )

    async def _check_one(self, registration: _ProviderRegistration) -> ComponentHealth:
        started = monotonic_now_ns()
        try:
            result = await registration.provider.health()
        except Exception as exc:
            latency_ms = (monotonic_now_ns() - started) / 1_000_000.0
            return ComponentHealth(
                component=registration.name,
                status=HealthStatus.FAILED,
                critical=registration.critical,
                detail=f"health check raised {type(exc).__name__}: {exc}",
                latency_ms=latency_ms,
            )

        latency_ms = (monotonic_now_ns() - started) / 1_000_000.0
        return result.model_copy(
            update={
                "component": registration.name,
                "critical": registration.critical,
                "latency_ms": latency_ms,
                "checked_at": utc_now(),
            }
        )


def aggregate_health(components: Iterable[ComponentHealth]) -> HealthStatus:
    """Aggregate component states conservatively.

    A failed critical component makes the system FAILED. Any other failure,
    degradation, or unknown component makes the aggregate DEGRADED. An empty
    registry is UNKNOWN rather than optimistically healthy.
    """
    items = tuple(components)
    if not items:
        return HealthStatus.UNKNOWN
    if any(item.critical and item.status is HealthStatus.FAILED for item in items):
        return HealthStatus.FAILED
    if any(item.status is not HealthStatus.HEALTHY for item in items):
        return HealthStatus.DEGRADED
    return HealthStatus.HEALTHY
