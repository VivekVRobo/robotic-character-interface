"""Snapshot serialization helpers."""

from rci.state.models import StateSnapshot


def snapshot_json(snapshot: StateSnapshot) -> str:
    """Serialize one immutable state snapshot for diagnostics/API use."""
    return snapshot.model_dump_json()
