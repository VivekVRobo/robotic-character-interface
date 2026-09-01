import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from rci.characters.contracts import SCHEMA_VERSION, MotionDisposition, parse_character_response

FORBIDDEN_PHYSICAL_FIELDS = {
    "angle",
    "angles",
    "joint",
    "joints",
    "motor",
    "motors",
    "pulse_width",
    "pwm",
    "servo",
    "servos",
    "target_position",
    "target_velocity",
    "trajectory",
}


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "interaction_id": "interaction_123",
        "decision_id": "dec_123",
        "source_character": "aurelia",
        "speech": {
            "text": "I can give you a structured assessment.",
            "delivery": "confident",
            "interruptible": True,
        },
        "expression": {"expression": "confident", "strength": "subtle"},
        "motion": {"cue": "present", "style": "restrained", "disposition": "optional"},
        "verified": True,
        "persistence_committed": True,
        "persistence_durable": True,
    }


def test_aurelia_character_response_is_accepted() -> None:
    response = parse_character_response(_valid_payload())
    assert response.schema_version == SCHEMA_VERSION
    assert response.motion.disposition == MotionDisposition.OPTIONAL


def test_extra_physical_control_field_is_rejected() -> None:
    payload = _valid_payload()
    motion = dict(payload["motion"])
    motion["servo"] = 90
    payload["motion"] = motion
    with pytest.raises(ValidationError):
        parse_character_response(payload)


def test_unverified_or_uncommitted_character_response_is_rejected() -> None:
    payload = _valid_payload()
    payload["verified"] = False
    with pytest.raises(ValidationError):
        parse_character_response(payload)

    payload = _valid_payload()
    payload["persistence_committed"] = False
    with pytest.raises(ValidationError):
        parse_character_response(payload)


def test_motion_can_never_be_required() -> None:
    payload = _valid_payload()
    motion = dict(payload["motion"])
    motion["disposition"] = "required"
    payload["motion"] = motion
    with pytest.raises(ValidationError):
        parse_character_response(payload)


def test_mirrored_schema_contains_no_physical_control_fields() -> None:
    schema = json.loads(
        Path("schemas/rci-character-response-v1.schema.json").read_text(encoding="utf-8")
    )
    assert schema["$id"] == SCHEMA_VERSION
    assert FORBIDDEN_PHYSICAL_FIELDS.isdisjoint(_collect_property_names(schema))


def _collect_property_names(value: object) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            names.update(str(key) for key in properties)
        for child in value.values():
            names.update(_collect_property_names(child))
    elif isinstance(value, list):
        for child in value:
            names.update(_collect_property_names(child))
    return names
