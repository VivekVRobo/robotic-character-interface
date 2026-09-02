import { describe, expect, it } from "vitest";
import { parseRobotTelemetry } from "./runtimeClient";

const telemetry = {
  uptimeMs: 1200,
  systemState: "IDLE",
  supplyMv: 6000,
  simulationOnly: true,
  measuredHardware: false,
  joints: [
    { jointId: 1, positionCdeg: 1000, velocityCdegS: 0, currentMa: 80 },
    { jointId: 2, positionCdeg: 3000, velocityCdegS: -120, currentMa: 125 },
  ],
};

describe("runtime telemetry contract", () => {
  it("accepts explicitly simulation-only digital-twin telemetry", () => {
    const parsed = parseRobotTelemetry(telemetry);
    expect(parsed.systemState).toBe("IDLE");
    expect(parsed.supplyMv).toBe(6000);
    expect(parsed.joints).toHaveLength(2);
    expect(parsed.simulationOnly).toBe(true);
    expect(parsed.measuredHardware).toBe(false);
  });

  it("rejects telemetry that claims measured hardware provenance", () => {
    expect(() =>
      parseRobotTelemetry({ ...telemetry, measuredHardware: true }),
    ).toThrow(/provenance/);
  });

  it("rejects duplicate joint identifiers", () => {
    expect(() =>
      parseRobotTelemetry({
        ...telemetry,
        joints: [telemetry.joints[0], telemetry.joints[0]],
      }),
    ).toThrow(/duplicate joint IDs/);
  });

  it("rejects impossible joint protocol values", () => {
    expect(() =>
      parseRobotTelemetry({
        ...telemetry,
        joints: [{ ...telemetry.joints[0], positionCdeg: 40000 }],
      }),
    ).toThrow(/positionCdeg/);
  });
});
