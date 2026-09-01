#include "runtime.h"

namespace {

constexpr unsigned long kSerialBaud = 115200;
constexpr size_t kReceiveCapacity =
    rci::protocol::kFrameOverhead + rci::protocol::kMaxPayloadSize;

rci::robot::RobotRuntime g_runtime;
uint8_t g_receive_buffer[kReceiveCapacity] = {};
size_t g_receive_length = 0;
size_t g_expected_frame_size = 0;

void ResetReceiveBuffer() {
  g_receive_length = 0;
  g_expected_frame_size = 0;
}

void IngestByte(uint8_t value, uint32_t now_ms) {
  if (g_receive_length == 0 && value != rci::protocol::kMagic0) {
    return;
  }

  if (g_receive_length == 1 && value != rci::protocol::kMagic1) {
    if (value == rci::protocol::kMagic0) {
      g_receive_buffer[0] = value;
      return;
    }
    ResetReceiveBuffer();
    return;
  }

  if (g_receive_length >= kReceiveCapacity) {
    ResetReceiveBuffer();
    return;
  }

  g_receive_buffer[g_receive_length++] = value;

  if (g_receive_length == rci::protocol::kHeaderSize) {
    const uint16_t payload_length = rci::robot::ReadU16Le(g_receive_buffer + 6);
    if (payload_length > rci::protocol::kMaxPayloadSize) {
      ResetReceiveBuffer();
      return;
    }
    g_expected_frame_size = rci::protocol::kFrameOverhead + payload_length;
  }

  if (g_expected_frame_size > 0 && g_receive_length == g_expected_frame_size) {
    // PR-012 dispatches protocol/safety state only. No actuator API exists here.
    (void)g_runtime.HandleFrame(g_receive_buffer, g_receive_length, now_ms);
    ResetReceiveBuffer();
  }
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);
  ResetReceiveBuffer();
}

void loop() {
  const uint32_t now_ms = millis();
  while (Serial.available() > 0) {
    const int next = Serial.read();
    if (next >= 0) {
      IngestByte(static_cast<uint8_t>(next), now_ms);
    }
  }
  g_runtime.Tick(now_ms);
}
