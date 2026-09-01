import pytest

from rci.domain.enums import HealthStatus
from rci.events.bus import EventBus
from rci.events.types import HealthChanged
from rci.health.models import ComponentHealth
from rci.health.monitor import HealthMonitor
from rci.health.registry import HealthRegistry


class MutableProvider:
    def __init__(self) -> None:
        self.status = HealthStatus.HEALTHY

    async def health(self) -> ComponentHealth:
        return ComponentHealth(component="placeholder", status=self.status)


@pytest.mark.asyncio
async def test_monitor_publishes_only_status_changes() -> None:
    bus = EventBus()
    registry = HealthRegistry()
    provider = MutableProvider()
    registry.register("robot", provider, critical=True)
    monitor = HealthMonitor(registry, bus)
    events: list[HealthChanged] = []

    async def collect(event: HealthChanged) -> None:
        events.append(event)

    bus.subscribe(HealthChanged, collect)
    await bus.start()
    await monitor.run_once()
    await monitor.run_once()
    provider.status = HealthStatus.FAILED
    await monitor.run_once()
    await bus.join()
    await bus.stop()

    assert [(item.previous_status, item.current_status) for item in events] == [
        (HealthStatus.UNKNOWN, HealthStatus.HEALTHY),
        (HealthStatus.HEALTHY, HealthStatus.FAILED),
    ]
