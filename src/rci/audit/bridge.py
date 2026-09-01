"""Event-bus bridge that records runtime events into the audit chain."""

from rci.audit.logger import AuditLogger
from rci.events.base import Event
from rci.events.bus import EventBus
from rci.events.handlers import Subscription


class EventAuditBridge:
    """Subscribe to all runtime events and append them to the audit log."""

    def __init__(self, event_bus: EventBus, audit_logger: AuditLogger) -> None:
        self._event_bus = event_bus
        self._audit_logger = audit_logger
        self._subscription: Subscription | None = None

    def start(self) -> None:
        if self._subscription is not None:
            return
        self._subscription = self._event_bus.subscribe(Event, self._handle)

    def stop(self) -> None:
        if self._subscription is None:
            return
        self._event_bus.unsubscribe(self._subscription)
        self._subscription = None

    async def _handle(self, event: Event) -> None:
        await self._audit_logger.append_event(event)
