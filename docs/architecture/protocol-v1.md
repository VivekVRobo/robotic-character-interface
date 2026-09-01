# RCI Binary Protocol v1

RCI protocol v1 is a little-endian, versioned binary frame shared by host Python and firmware C++.

## Frame

```text
MAGIC[2] VERSION[1] TYPE[1] SEQUENCE[2] PAYLOAD_LENGTH[2] PAYLOAD[N] CRC16[2]
```

- Magic: ASCII `RC` (`0x52 0x43`).
- Version: `1`.
- Sequence: unsigned 16-bit little-endian.
- Payload length: unsigned 16-bit little-endian, maximum 512 bytes.
- CRC: CRC-16/CCITT-FALSE over every byte from magic through the end of payload. Polynomial `0x1021`, initial value `0xFFFF`, no reflection, no final XOR.
- Strict decoders reject bad magic, unsupported versions, unknown message types, oversized declarations, truncation, trailing bytes, and checksum mismatch.

## Message types

1. `GLOVE_TELEMETRY`
2. `HEARTBEAT`
3. `VALIDATED_MOTION_COMMAND`
4. `ESTOP`
5. `ACK`
6. `NACK`
7. `ROBOT_TELEMETRY`

The glove never transmits servo or joint commands. Its compact telemetry payload is 21 bytes, giving a 31-byte complete frame that fits one nRF24 32-byte payload.

## Glove telemetry payload

```text
u16 device_time_ms_mod
s16 accel_x_mg
s16 accel_y_mg
s16 accel_z_mg
s16 gyro_x_cdeg_s
s16 gyro_y_cdeg_s
s16 gyro_z_cdeg_s
s16 pitch_cdeg
s16 roll_cdeg
u16 battery_mv
u8  flags
```

Sequence lives in the frame header. Values use scaled integers so the radio packet does not depend on floating-point ABI layout.

## Validated motion command

This message exists only downstream of deterministic motion safety. It contains a UUID command identifier, TTL, motion mode, bounded `(joint_id, target_cdeg)` entries, and safety-approved velocity/acceleration ceilings. It never contains raw PWM or servo pulse widths.

Freshness on the MCU is based on receive time plus TTL and sequence/replay checks; a host monotonic timestamp is intentionally not placed on the wire because host and MCU clocks are not synchronized.

## Cross-language contract

Python and C++ both verify the standard CRC check vector `123456789 -> 0x29B1`. Golden fixtures also lock the glove payload and frame prefix byte-for-byte. CI compiles and executes the firmware-side golden-vector test with `g++` in addition to the Python contract suite.
