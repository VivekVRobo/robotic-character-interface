"""Strict HTTP boundary from RCI into the external Aurelia character engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import httpx

from rci.characters.contracts import CharacterResponseV1, parse_character_response
from rci.cognition.meaning import MeaningFrame


class CharacterEngineError(RuntimeError):
    """Raised when a character engine cannot return a publishable RCI contract."""


class CharacterEngine(Protocol):
    async def respond(self, frame: MeaningFrame) -> CharacterResponseV1: ...


class AureliaCharacterClient:
    """Call Aurelia's hardened cognitive endpoint and validate its embodiment response."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:5000",
        timeout_s: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("character engine timeout must be positive")
        self._owns_client = http_client is None
        self._client = (
            httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout_s)
            if http_client is None
            else http_client
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def respond(self, frame: MeaningFrame) -> CharacterResponseV1:
        message = self._render_message(frame)
        try:
            response = await self._client.post("/api/cognitive-cycle", json={"message": message})
        except httpx.HTTPError as exc:
            raise CharacterEngineError(f"Aurelia request failed: {exc}") from exc
        if response.status_code != 200:
            raise CharacterEngineError(
                f"Aurelia rejected cognitive cycle with HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise CharacterEngineError("Aurelia returned invalid JSON") from exc
        if not isinstance(payload, Mapping):
            raise CharacterEngineError("Aurelia response must be a JSON object")
        if payload.get("safe_to_publish") is not True:
            raise CharacterEngineError("Aurelia response is not safe to publish")
        character_payload = payload.get("character_response")
        if not isinstance(character_payload, Mapping):
            raise CharacterEngineError("Aurelia response is missing character_response")
        try:
            return parse_character_response(_string_key_mapping(character_payload))
        except Exception as exc:
            raise CharacterEngineError("Aurelia character_response failed RCI validation") from exc

    @staticmethod
    def _render_message(frame: MeaningFrame) -> str:
        if frame.text.strip():
            if frame.gesture is None:
                return frame.text.strip()
            return f"{frame.text.strip()}\n\nObserved motion gesture: {frame.gesture.value}."
        if frame.gesture is None:
            raise CharacterEngineError("meaning frame has no character-engine input")
        return f"Observed user motion gesture: {frame.gesture.value}."


def _string_key_mapping(value: Mapping[object, Any]) -> dict[str, object]:
    converted: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise CharacterEngineError("character_response contains a non-string key")
        converted[key] = item
    return converted
