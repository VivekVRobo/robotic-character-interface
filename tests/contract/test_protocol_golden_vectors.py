import json
from pathlib import Path

from rci.protocols.checksums import crc16_ccitt_false
from rci.protocols.constants import DeviceSource, MessageType, WireSystemState
from rci.protocols.framing import Frame
from rci.protocols.messages import GloveTelemetry, Heartbeat

FIXTURE = Path("tests/fixtures/protocol/golden_vectors.json")


def _vectors() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_crc_golden_vector() -> None:
    vectors = _vectors()
    crc_vector = vectors["crc16_ccitt_false"]
    assert isinstance(crc_vector, dict)
    payload = bytes.fromhex(str(crc_vector["input_hex"]))
    expected = int(str(crc_vector["expected_crc_hex"]), 16)
    assert crc16_ccitt_false(payload) == expected


def test_glove_payload_and_frame_prefix_golden_vector() -> None:
    vector = _vectors()["glove_telemetry"]
    assert isinstance(vector, dict)
    telemetry = GloveTelemetry(
        0x3456,
        1000,
        -250,
        42,
        1250,
        -330,
        0,
        1234,
        -567,
        3975,
        5,
    )
    payload = telemetry.encode()
    assert payload.hex() == vector["payload_hex"]
    frame = Frame(MessageType.GLOVE_TELEMETRY, int(vector["sequence"]), payload).encode()
    assert len(frame) == vector["frame_size"]
    assert frame[:-2].hex() == vector["frame_prefix_hex"]
    assert int.from_bytes(frame[-2:], "little") == crc16_ccitt_false(frame[:-2])


def test_heartbeat_payload_and_frame_prefix_golden_vector() -> None:
    vector = _vectors()["heartbeat"]
    assert isinstance(vector, dict)
    heartbeat = Heartbeat(DeviceSource.ROBOT, 123456, WireSystemState.IDLE)
    payload = heartbeat.encode()
    assert payload.hex() == vector["payload_hex"]
    frame = Frame(MessageType.HEARTBEAT, int(vector["sequence"]), payload).encode()
    assert frame[:-2].hex() == vector["frame_prefix_hex"]
