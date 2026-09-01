#include <stdint.h>

#include "../../firmware/shared/protocol.h"

int main() {
  const uint8_t crc_input[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
  if (rci::protocol::Crc16CcittFalse(crc_input, sizeof(crc_input)) != 0x29B1u) {
    return 1;
  }

  const rci::protocol::GloveTelemetry telemetry = {
      0x3456u, 1000, -250, 42, 1250, -330, 0, 1234, -567, 3975u, 5u};
  uint8_t payload[rci::protocol::kGloveTelemetryPayloadSize] = {};
  if (rci::protocol::EncodeGloveTelemetryPayload(telemetry, payload, sizeof(payload)) !=
      rci::protocol::kGloveTelemetryPayloadSize) {
    return 2;
  }
  const uint8_t expected_payload[] = {
      0x56, 0x34, 0xE8, 0x03, 0x06, 0xFF, 0x2A, 0x00, 0xE2, 0x04, 0xB6,
      0xFE, 0x00, 0x00, 0xD2, 0x04, 0xC9, 0xFD, 0x87, 0x0F, 0x05};
  for (size_t i = 0; i < sizeof(expected_payload); ++i) {
    if (payload[i] != expected_payload[i]) {
      return 3;
    }
  }

  uint8_t frame[rci::protocol::kGloveTelemetryFrameSize] = {};
  const size_t frame_size = rci::protocol::BuildFrame(
      rci::protocol::MessageType::kGloveTelemetry,
      0x1234u,
      payload,
      static_cast<uint16_t>(sizeof(payload)),
      frame,
      sizeof(frame));
  if (frame_size != rci::protocol::kGloveTelemetryFrameSize) {
    return 4;
  }
  const uint8_t expected_prefix[] = {
      0x52, 0x43, 0x01, 0x01, 0x34, 0x12, 0x15, 0x00, 0x56, 0x34,
      0xE8, 0x03, 0x06, 0xFF, 0x2A, 0x00, 0xE2, 0x04, 0xB6, 0xFE,
      0x00, 0x00, 0xD2, 0x04, 0xC9, 0xFD, 0x87, 0x0F, 0x05};
  for (size_t i = 0; i < sizeof(expected_prefix); ++i) {
    if (frame[i] != expected_prefix[i]) {
      return 5;
    }
  }
  const uint16_t frame_crc = static_cast<uint16_t>(frame[29]) |
                             (static_cast<uint16_t>(frame[30]) << 8);
  if (frame_crc != rci::protocol::Crc16CcittFalse(frame, 29)) {
    return 6;
  }
  return 0;
}
