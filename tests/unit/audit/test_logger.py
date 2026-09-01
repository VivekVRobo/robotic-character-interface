from pathlib import Path

import pytest

from rci.audit.hash_chain import AuditIntegrityError
from rci.audit.logger import AuditLogger
from rci.events.types import EmergencyStopTriggered


@pytest.mark.asyncio
async def test_file_log_round_trips_and_verifies(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    logger = AuditLogger(path)
    await logger.append(event_type="system.started", source="test", payload={"version": "1"})
    await logger.append_event(EmergencyStopTriggered(source="safety", reason="button"))

    loaded = AuditLogger(path)

    assert len(loaded.entries) == 2
    assert loaded.entries[1].event_type == "safety.estop_triggered"
    loaded.verify()


@pytest.mark.asyncio
async def test_corrupted_durable_log_fails_on_reload(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    logger = AuditLogger(path)
    await logger.append(event_type="safe", source="test", payload={"value": 1})
    text = path.read_text(encoding="utf-8").replace('"value":1', '"value":2')
    path.write_text(text, encoding="utf-8")

    with pytest.raises(AuditIntegrityError):
        AuditLogger(path)
