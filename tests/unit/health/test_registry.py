import pytest

from rci.domain.enums import HealthStatus
from rci.health.models import ComponentHealth
from rci.health.registry import HealthRegistry, aggregate_health


class StaticProvider:
    def __init__(self, status: HealthStatus) -> None:
        self.status = status

    async def health(self) -> ComponentHealth:
        return ComponentHealth(component="ignored", status=self.status)


class ExplodingProvider:
    async def health(self) -> ComponentHealth:
        raise RuntimeError("device vanished")


def test_empty_aggregate_is_unknown() -> None:
    assert aggregate_health([]) is HealthStatus.UNKNOWN


def test_noncritical_failure_degrades_aggregate() -> None:
    components = [
        ComponentHealth(component="voice", status=HealthStatus.FAILED, critical=False),
        ComponentHealth(component="robot", status=HealthStatus.HEALTHY, critical=True),
    ]
    assert aggregate_health(components) is HealthStatus.DEGRADED


def test_critical_failure_fails_aggregate() -> None:
    components = [
        ComponentHealth(component="robot", status=HealthStatus.FAILED, critical=True)
    ]
    assert aggregate_health(components) is HealthStatus.FAILED


@pytest.mark.asyncio
async def test_registry_overrides_provider_name_and_criticality() -> None:
    registry = HealthRegistry()
    registry.register("robot", StaticProvider(HealthStatus.HEALTHY), critical=True)

    report = await registry.check_all()

    assert report.overall is HealthStatus.HEALTHY
    assert report.components["robot"].critical is True
    assert report.components["robot"].latency_ms is not None


@pytest.mark.asyncio
async def test_provider_exception_becomes_failed_health_not_monitor_crash() -> None:
    registry = HealthRegistry()
    registry.register("robot", ExplodingProvider(), critical=True)

    report = await registry.check_all()

    assert report.overall is HealthStatus.FAILED
    assert report.components["robot"].status is HealthStatus.FAILED
    assert "RuntimeError" in (report.components["robot"].detail or "")


def test_duplicate_registration_is_rejected() -> None:
    registry = HealthRegistry()
    provider = StaticProvider(HealthStatus.HEALTHY)
    registry.register("robot", provider)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("robot", provider)
