"""Atomic JSON IO for single-servo HIL evidence and activation permits."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from rci.hil.models import HilActivationPermit, SingleServoHilEvidence


class HilEvidenceError(ValueError):
    """Raised when a HIL evidence or permit document is unreadable or invalid."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HilEvidenceError(f"unable to read HIL document {path}: {exc}") from exc


def load_evidence(path: Path) -> SingleServoHilEvidence:
    try:
        return SingleServoHilEvidence.model_validate(_read_json(path))
    except ValidationError as exc:
        raise HilEvidenceError(f"invalid single-servo HIL evidence: {exc}") from exc


def load_permit(path: Path) -> HilActivationPermit:
    try:
        return HilActivationPermit.model_validate(_read_json(path))
    except ValidationError as exc:
        raise HilEvidenceError(f"invalid single-servo HIL permit: {exc}") from exc


def write_permit(path: Path, permit: HilActivationPermit) -> None:
    """Atomically write a machine-readable permit without mutating production config."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    payload = permit.model_dump_json(indent=2) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise HilEvidenceError(f"unable to write HIL permit {path}: {exc}") from exc
