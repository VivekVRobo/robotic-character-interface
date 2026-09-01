from rci.behavior import BehaviorPlanner
from rci.characters.contracts import CharacterResponseV1


def _response(*, cue: str, disposition: str) -> CharacterResponseV1:
    return CharacterResponseV1.model_validate(
        {
            "schema_version": "rci.character_response.v1",
            "interaction_id": "interaction_1",
            "decision_id": "decision_1",
            "source_character": "aurelia",
            "speech": {
                "text": "Verified response.",
                "delivery": "confident",
                "interruptible": True,
            },
            "expression": {"expression": "confident", "strength": "subtle"},
            "motion": {
                "cue": cue,
                "style": "restrained",
                "disposition": disposition,
            },
            "verified": True,
            "persistence_committed": True,
            "persistence_durable": False,
        }
    )


def test_none_motion_yields_no_behavior_intent() -> None:
    assert BehaviorPlanner().plan(_response(cue="none", disposition="none")) is None


def test_optional_semantic_motion_preserves_character_lineage() -> None:
    intent = BehaviorPlanner().plan(_response(cue="present", disposition="optional"))

    assert intent is not None
    assert intent.interaction_id == "interaction_1"
    assert intent.decision_id == "decision_1"
    assert intent.source_character == "aurelia"
    assert intent.expression == "confident"
    assert intent.cue.value == "present"
    assert intent.style.value == "restrained"
    assert not hasattr(intent, "joint_targets_deg")
    assert not hasattr(intent, "pwm")
    assert not hasattr(intent, "servo")
