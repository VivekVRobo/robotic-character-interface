"""Canonical SHA-256 audit-chain hashing and verification."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from rci.audit.models import GENESIS_HASH, AuditEntry
from rci.domain.errors import RCIError


class AuditIntegrityError(RCIError):
    """Audit chain is malformed or has been modified."""


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_entry_hash(fields: dict[str, Any]) -> str:
    encoded = canonical_json(fields).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hashable_fields(entry: AuditEntry) -> dict[str, Any]:
    return entry.model_dump(mode="json", exclude={"entry_hash"})


def verify_chain(entries: Iterable[AuditEntry]) -> None:
    expected_previous = GENESIS_HASH
    expected_sequence = 0
    for entry in entries:
        if entry.sequence != expected_sequence:
            raise AuditIntegrityError(
                f"audit sequence mismatch at {entry.sequence}; expected {expected_sequence}"
            )
        if entry.previous_hash != expected_previous:
            raise AuditIntegrityError(f"audit previous-hash mismatch at sequence {entry.sequence}")
        expected_hash = compute_entry_hash(hashable_fields(entry))
        if entry.entry_hash != expected_hash:
            raise AuditIntegrityError(f"audit entry hash mismatch at sequence {entry.sequence}")
        expected_previous = entry.entry_hash
        expected_sequence += 1
