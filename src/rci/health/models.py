"""Health reporting models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from rci.domain.enums import HealthStatus
from rci.domain.timestamps import utc_now


class ComponentHealth(BaseModel):
    """One component's latest health result."""

    model_config = ConfigDict(frozen=True)

    component: str = Field(min_length=1)
    status: HealthStatus
    critical: bool = False
    detail: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    checked_at: datetime = Field(default_factory=utc_now)


class HealthReport(BaseModel):
    """Immutable aggregate health snapshot."""

    model_config = ConfigDict(frozen=True)

    overall: HealthStatus
    components: dict[str, ComponentHealth]
    checked_at: datetime = Field(default_factory=utc_now)

    @property
    def healthy(self) -> bool:
        return self.overall is HealthStatus.HEALTHY
