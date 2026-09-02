from fastapi.testclient import TestClient

from rci.api import create_api_app
from rci.characters.contracts import CharacterResponseV1
from rci.cognition.meaning import MeaningFrame


class StubEngine:
    async def respond(self, frame: MeaningFrame) -> CharacterResponseV1:
        return CharacterResponseV1.model_validate(
            {
                "schema_version": "rci.character_response.v1",
                "interaction_id": "interaction_1",
                "decision_id": "decision_1",
                "source_character": "aurelia",
                "speech": {
                    "text": f"Received: {frame.text}",
                    "delivery": "neutral",
                    "interruptible": True,
                },
                "expression": {"expression": "neutral", "strength": "subtle"},
                "motion": {
                    "cue": "none",
                    "style": "restrained",
                    "disposition": "none",
                },
                "verified": True,
                "persistence_committed": True,
                "persistence_durable": False,
            }
        )


def test_status_is_explicitly_simulation_only() -> None:
    response = TestClient(create_api_app(StubEngine())).get("/api/status")
    assert response.status_code == 200
    assert response.json() == {
        "software_mode": "simulation",
        "hardware_verified": False,
        "physical_motion_enabled": False,
        "character_engine": "external",
    }


def test_simulation_interaction_returns_semantics_without_actuator_command() -> None:
    client = TestClient(create_api_app(StubEngine()))
    response = client.post(
        "/api/simulation/interact",
        json={
            "simulation": True,
            "timestamp_ms": 1000,
            "text": "hello",
            "gesture": "wave",
            "gesture_confidence": 0.8,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meaning"]["gesture"] == "wave"
    assert payload["character_response"]["verified"] is True
    assert payload["actuator_command_emitted"] is False
    assert payload["behavior"] is None


def test_api_rejects_text_and_voice_in_same_turn() -> None:
    response = TestClient(create_api_app(StubEngine())).post(
        "/api/simulation/interact",
        json={
            "simulation": True,
            "timestamp_ms": 1,
            "text": "typed",
            "voice_text": "spoken",
        },
    )
    assert response.status_code == 422
