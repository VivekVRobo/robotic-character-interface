import pytest

from rci.audit.bridge import EventAuditBridge
from rci.audit.logger import AuditLogger
from rci.events.bus import EventBus
from rci.events.types import SystemStarted


@pytest.mark.asyncio
async def test_event_bridge_audits_runtime_events() -> None:
    bus = EventBus()
    logger = AuditLogger()
    bridge = EventAuditBridge(bus, logger)
    bridge.start()
    await bus.start()

    await bus.publish(SystemStarted(source="system", version="0.1"))
    await bus.join()
    await bus.stop()
    bridge.stop()

    assert len(logger.entries) == 1
    assert logger.entries[0].event_type == "system.started"
    assert logger.entries[0].payload["version"] == "0.1"
