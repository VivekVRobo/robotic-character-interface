"""Periodic health monitoring and change events."""

from __future__ import annotations

import asyncio

from rci.domain.enums import HealthStatus
from rci.events.base import EventPriority
from rci.events.bus import EventBus
from rci.events.types import HealthChanged
from rci.health.models import HealthReport
from rci.health.registry import HealthRegistry


class HealthMonitor:
    """Poll health providers and publish only component status transitions."""

    def __init__(
        self,
        registry: HealthRegistry,
        event_bus: EventBus,
        *,
        interval_seconds: float = 1.0,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._registry = registry
        self._event_bus = event_bus
        self._interval_seconds = interval_seconds
        self._previous: dict[str, HealthStatus] = {}
        self._latest: HealthReport | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def latest(self) -> HealthReport | None:
        return self._latest

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def run_once(self) -> HealthReport:
        report = await self._registry.check_all()
        for name, component in report.components.items():
            previous = self._previous.get(name, HealthStatus.UNKNOWN)
            if component.status is not previous:
                priority = (
                    EventPriority.CRITICAL
                    if component.critical and component.status is HealthStatus.FAILED
                    else EventPriority.NORMAL
                )
                await self._event_bus.publish(
                    HealthChanged(
                        source="health-monitor",
                        component=name,
                        previous_status=previous,
                        current_status=component.status,
                        detail=component.detail,
                    ),
                    priority=priority,
                )
            self._previous[name] = component.status
        self._latest = report
        return report

    async def start(self) -> None:
        if self.is_running:
            return
        self._task = asyncio.create_task(self._run_loop(), name="rci-health-monitor")

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _run_loop(self) -> None:
        try:
            while True:
                await self.run_once()
                await asyncio.sleep(self._interval_seconds)
        except asyncio.CancelledError:
            raise
