"""Tamper-evident audit entry models."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from rci.domain.timestamps import utc_now

GENESIS_HASH = "0" * 64


class AuditEntry(BaseModel):
    """One append-only audit record linked to the previous entry hash."""

    model_config = ConfigDict(frozen=True)

    entry_id: UUID = Field(default_factory=uuid4)
    sequence: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    interaction_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = Field(min_length=64, max_length=64)
    entry_hash: str = Field(min_length=64, max_length=64)
