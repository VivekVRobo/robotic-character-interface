"""Audit-query helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from rci.audit.models import AuditEntry


@dataclass(frozen=True, slots=True)
class AuditQuery:
    event_type: str | None = None
    source: str | None = None
    interaction_id: UUID | None = None


def query_entries(entries: Iterable[AuditEntry], query: AuditQuery) -> tuple[AuditEntry, ...]:
    result: list[AuditEntry] = []
    for entry in entries:
        if query.event_type is not None and entry.event_type != query.event_type:
            continue
        if query.source is not None and entry.source != query.source:
            continue
        if query.interaction_id is not None and entry.interaction_id != query.interaction_id:
            continue
        result.append(entry)
    return tuple(result)
