from rci.state.models import StateSnapshot
from rci.state.snapshot import snapshot_json


def test_snapshot_serializes_for_diagnostics() -> None:
    payload = snapshot_json(StateSnapshot())
    assert '"state":"BOOT"' in payload
    assert '"motion_authorized":false' in payload
