"""Append-only-by-contract audit logger with hash-chain verification."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from rci.audit.hash_chain import AuditIntegrityError, compute_entry_hash, verify_chain
from rci.audit.models import GENESIS_HASH, AuditEntry
from rci.domain.errors import RCIError
from rci.domain.timestamps import utc_now
from rci.events.base import Event


class AuditStorageError(RCIError):
    """Audit storage could not be loaded or appended safely."""


class AuditLogger:
    """Maintain an in-memory chain and optional durable JSONL append log."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._entries = self._load(path) if path is not None else []
        verify_chain(self._entries)
        self._lock = asyncio.Lock()

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    async def append(
        self,
        *,
        event_type: str,
        source: str,
        payload: dict[str, Any] | None = None,
        interaction_id: UUID | None = None,
    ) -> AuditEntry:
        async with self._lock:
            previous_hash = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
            fields: dict[str, Any] = {
                "entry_id": str(uuid4()),
                "sequence": len(self._entries),
                "timestamp": utc_now().isoformat().replace("+00:00", "Z"),
                "event_type": event_type,
                "source": source,
                "interaction_id": str(interaction_id) if interaction_id is not None else None,
                "payload": {} if payload is None else payload,
                "previous_hash": previous_hash,
            }
            entry_hash = compute_entry_hash(fields)
            entry = AuditEntry.model_validate({**fields, "entry_hash": entry_hash})
            if self._path is not None:
                line = entry.model_dump_json() + "\n"
                await asyncio.to_thread(self._append_line, self._path, line)
            self._entries.append(entry)
            return entry

    async def append_event(self, event: Event) -> AuditEntry:
        payload = event.model_dump(mode="json")
        return await self.append(
            event_type=event.event_type,
            source=event.source,
            interaction_id=event.interaction_id,
            payload=payload,
        )

    def verify(self) -> None:
        verify_chain(self._entries)

    @staticmethod
    def _append_line(path: Path, line: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise AuditStorageError(f"failed to append audit record: {exc}") from exc

    @staticmethod
    def _load(path: Path) -> list[AuditEntry]:
        if not path.exists():
            return []
        entries: list[AuditEntry] = []
        try:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                    entries.append(AuditEntry.model_validate(raw))
                except (json.JSONDecodeError, ValidationError) as exc:
                    raise AuditIntegrityError(
                        f"invalid audit record at line {line_number}"
                    ) from exc
        except OSError as exc:
            raise AuditStorageError(f"failed to read audit log: {exc}") from exc
        return entries
