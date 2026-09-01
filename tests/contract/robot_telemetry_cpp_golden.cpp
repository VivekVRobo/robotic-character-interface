#include <array>
#include <cassert>
#include <cstdint>

#include "../../firmware/shared/protocol.h"

int main() {
  rci::protocol::RobotTelemetry telemetry{};
  telemetry.uptime_ms = 123456u;
  telemetry.state = 0x06u;
  telemetry.flags = 0x03u;
  telemetry.supply_mv = 6000u;
  telemetry.joint_count = 4u;
  telemetry.joints[0] = {1u, 1250, 240, 210u};
  telemetry.joints[1] = {2u, -350, -120, 180u};
  telemetry.joints[2] = {3u, 9050, 0, 95u};
  telemetry.joints[3] = {4u, 2000, 15, 110u};

  std::array<uint8_t, 64> encoded{};
  const size_t size = rci::protocol::EncodeRobotTelemetryPayload(
      telemetry, encoded.data(), encoded.size());
  assert(size == 37u);

  const std::array<uint8_t, 37> expected = {
      0x40, 0xE2, 0x01, 0x00, 0x06, 0x03, 0x70, 0x17, 0x04,
      0x01, 0xE2, 0x04, 0xF0, 0x00, 0xD2, 0x00,
      0x02, 0xA2, 0xFE, 0x88, 0xFF, 0xB4, 0x00,
      0x03, 0x5A, 0x23, 0x00, 0x00, 0x5F, 0x00,
      0x04, 0xD0, 0x07, 0x0F, 0x00, 0x6E, 0x00,
  };
  for (size_t index = 0; index < expected.size(); ++index) {
    assert(encoded[index] == expected[index]);
  }

  return 0;
}
