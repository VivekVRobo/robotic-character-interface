from rci.protocols.checksums import crc16_ccitt_false


def test_crc16_ccitt_false_standard_check_vector() -> None:
    assert crc16_ccitt_false(b"123456789") == 0x29B1
