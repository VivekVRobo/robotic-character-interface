"""Strong identifier aliases for traceable interactions and commands."""

from typing import NewType
from uuid import UUID, uuid4

EventId = NewType("EventId", UUID)
InteractionId = NewType("InteractionId", UUID)
CommandId = NewType("CommandId", UUID)
TrajectoryId = NewType("TrajectoryId", UUID)
SessionId = NewType("SessionId", UUID)
CharacterId = NewType("CharacterId", str)


def new_event_id() -> EventId:
    return EventId(uuid4())


def new_interaction_id() -> InteractionId:
    return InteractionId(uuid4())


def new_command_id() -> CommandId:
    return CommandId(uuid4())


def new_trajectory_id() -> TrajectoryId:
    return TrajectoryId(uuid4())


def new_session_id() -> SessionId:
    return SessionId(uuid4())
