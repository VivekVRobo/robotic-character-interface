from pathlib import Path

from rci.version import PROTOCOL_VERSION


def test_python_and_firmware_protocol_versions_match() -> None:
    header = Path("firmware/shared/protocol.h").read_text(encoding="utf-8")
    assert PROTOCOL_VERSION == 1
    assert "kProtocolVersion = 1" in header
