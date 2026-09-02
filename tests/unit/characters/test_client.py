import httpx
import pytest

from rci.characters.client import AureliaCharacterClient, CharacterEngineError
from rci.cognition.meaning import MeaningFrame
from rci.domain.enums import InteractionMode


def _character_response() -> dict[str, object]:
    return {
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
            "cue": "present",
            "style": "restrained",
            "disposition": "optional",
        },
        "verified": True,
        "persistence_committed": True,
        "persistence_durable": False,
    }


@pytest.mark.asyncio
async def test_client_accepts_only_publishable_valid_character_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/cognitive-cycle"
        return httpx.Response(
            200,
            json={"safe_to_publish": True, "character_response": _character_response()},
        )

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://aurelia.test",
    )
    client = AureliaCharacterClient(http_client=http_client)
    response = await client.respond(MeaningFrame("hello", InteractionMode.TEXT, 1, 1.0))
    await http_client.aclose()

    assert response.verified is True
    assert response.motion.cue.value == "present"


@pytest.mark.asyncio
async def test_client_fails_closed_on_nonpublishable_aurelia_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"safe_to_publish": False, "character_response": _character_response()},
        )

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://aurelia.test",
    )
    client = AureliaCharacterClient(http_client=http_client)
    with pytest.raises(CharacterEngineError, match="not safe to publish"):
        await client.respond(MeaningFrame("hello", InteractionMode.TEXT, 1, 1.0))
    await http_client.aclose()


@pytest.mark.asyncio
async def test_client_fails_closed_when_actuator_field_is_injected() -> None:
    poisoned = _character_response()
    poisoned["servo_angle"] = 90

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"safe_to_publish": True, "character_response": poisoned},
        )

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://aurelia.test",
    )
    client = AureliaCharacterClient(http_client=http_client)
    with pytest.raises(CharacterEngineError, match="failed RCI validation"):
        await client.respond(MeaningFrame("hello", InteractionMode.TEXT, 1, 1.0))
    await http_client.aclose()
