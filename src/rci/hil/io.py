"""Atomic JSON IO for single-servo HIL evidence, permits, and run results."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from rci.hil.models import HilActivationPermit, SingleServoHilEvidence, SingleServoHilRunResult


class HilEvidenceError(ValueError):
    """Raised when a HIL evidence, permit, or run-result document is invalid."""


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


def load_run_result(path: Path) -> SingleServoHilRunResult:
    try:
        return SingleServoHilRunResult.model_validate(_read_json(path))
    except ValidationError as exc:
        raise HilEvidenceError(f"invalid single-servo HIL run result: {exc}") from exc


def _write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    payload = model.model_dump_json(indent=2) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise HilEvidenceError(f"unable to write HIL document {path}: {exc}") from exc


def write_permit(path: Path, permit: HilActivationPermit) -> None:
    """Atomically write a permit without mutating production config."""
    _write_model(path, permit)


def write_run_result(path: Path, result: SingleServoHilRunResult) -> None:
    """Atomically persist the physical HIL outcome for later review."""
    _write_model(path, result)
