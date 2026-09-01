#include "runtime.h"

namespace {

constexpr unsigned long kSerialBaud = 115200;
constexpr size_t kReceiveCapacity =
    rci::protocol::kFrameOverhead + rci::protocol::kMaxPayloadSize;
constexpr size_t kAckFrameCapacity =
    rci::protocol::kFrameOverhead + rci::protocol::kAcknowledgementPayloadSize;

rci::robot::RobotRuntime g_runtime;
uint8_t g_receive_buffer[kReceiveCapacity] = {};
size_t g_receive_length = 0;
size_t g_expected_frame_size = 0;
uint16_t g_tx_sequence = 0;

void ResetReceiveBuffer() {
  g_receive_length = 0;
  g_expected_frame_size = 0;
}

void SendAcknowledgement(uint16_t request_sequence,
                         rci::robot::DispatchResult result) {
  if (result == rci::robot::DispatchResult::kRejectedInvalidFrame) {
    return;
  }

  const rci::protocol::AckStatus status = rci::robot::AckStatusForDispatch(result);
  const rci::protocol::MessageType type =
      status == rci::protocol::AckStatus::kOk ? rci::protocol::MessageType::kAck
                                              : rci::protocol::MessageType::kNack;
  uint8_t payload[rci::protocol::kAcknowledgementPayloadSize] = {};
  const size_t payload_size = rci::protocol::EncodeAcknowledgementPayload(
      request_sequence, status, payload, sizeof(payload));
  if (payload_size == 0) {
    return;
  }

  uint8_t frame[kAckFrameCapacity] = {};
  const size_t frame_size = rci::protocol::BuildFrame(
      type,
      g_tx_sequence++,
      payload,
      static_cast<uint16_t>(payload_size),
      frame,
      sizeof(frame));
  if (frame_size > 0) {
    Serial.write(frame, frame_size);
  }
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
    const uint16_t request_sequence = rci::robot::ReadU16Le(g_receive_buffer + 4);
    const rci::robot::DispatchResult result =
        g_runtime.HandleFrame(g_receive_buffer, g_receive_length, now_ms);
    SendAcknowledgement(request_sequence, result);
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
