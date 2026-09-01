"""Strict loader for simulation-only reference robot profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from rci.robotics.models import ReferenceRobotProfile


class ReferenceProfileError(ValueError):
    """Raised when a simulation reference profile is missing or invalid."""


def load_reference_profile(path: Path) -> ReferenceRobotProfile:
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReferenceProfileError(f"unable to load reference profile {path}: {exc}") from exc

    if not isinstance(raw, dict) or not isinstance(raw.get("reference_robot"), dict):
        raise ReferenceProfileError("reference profile must contain a 'reference_robot' mapping")

    try:
        return ReferenceRobotProfile.model_validate(raw["reference_robot"])
    except ValidationError as exc:
        raise ReferenceProfileError(f"invalid reference robot profile: {exc}") from exc
