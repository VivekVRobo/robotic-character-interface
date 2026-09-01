"""Health-provider interfaces and helpers."""

from __future__ import annotations

from typing import Protocol

from rci.health.models import ComponentHealth


class HealthProvider(Protocol):
    """Subsystem contract for active health checks."""

    async def health(self) -> ComponentHealth: ...
