import { describe, expect, it } from "vitest";

import {
  parseCharacterResponse,
  parseDashboardSnapshot,
} from "./contracts";

function validSnapshot(): unknown {
  return {
    connection: "connected",
    systemState: "ARMED",
    estopLatched: false,
    heartbeatHealthy: true,
    gatewayError: null,
    telemetry: {
      lastFrameSequence: 42,
      heartbeatAgeMs: 25,
      sentCount: 10,
      acknowledgedCount: 9,
      rejectedCount: 1,
    },
  };
}

function validCharacterResponse(): Record<string, unknown> {
  return {
    schema_version: "rci.character_response.v1",
    interaction_id: "interaction-1",
    decision_id: "decision-1",
    source_character: "aurelia",
    speech: {
      text: "Here is the verified response.",
      delivery: "neutral",
      interruptible: true,
    },
    expression: {
      expression: "neutral",
      strength: "subtle",
    },
    motion: {
      cue: "acknowledge",
      style: "restrained",
      disposition: "optional",
    },
    verified: true,
    persistence_committed: true,
    persistence_durable: false,
  };
}

describe("parseDashboardSnapshot", () => {
  it("accepts a finite connected ARMED snapshot", () => {
    const parsed = parseDashboardSnapshot(validSnapshot());
    expect(parsed.systemState).toBe("ARMED");
    expect(parsed.telemetry.lastFrameSequence).toBe(42);
  });

  it("rejects a healthy heartbeat while disconnected", () => {
    const value = validSnapshot() as Record<string, unknown>;
    value.connection = "disconnected";
    expect(() => parseDashboardSnapshot(value)).toThrow(/heartbeat cannot be healthy/);
  });

  it("rejects ESTOP state without an authoritative latched E-stop", () => {
    const value = validSnapshot() as Record<string, unknown>;
    value.systemState = "ESTOP";
    expect(() => parseDashboardSnapshot(value)).toThrow(/requires a latched E-stop/);
  });

  it("rejects malformed or out-of-range telemetry", () => {
    const value = validSnapshot() as Record<string, unknown>;
    const telemetry = value.telemetry as Record<string, unknown>;
    telemetry.lastFrameSequence = 65536;
    expect(() => parseDashboardSnapshot(value)).toThrow(/lastFrameSequence/);

    telemetry.lastFrameSequence = 42;
    telemetry.heartbeatAgeMs = Number.NaN;
    expect(() => parseDashboardSnapshot(value)).toThrow(/heartbeatAgeMs/);
  });
});

describe("parseCharacterResponse", () => {
  it("accepts the verified committed actuator-free Aurelia contract", () => {
    const parsed = parseCharacterResponse(validCharacterResponse());
    expect(parsed.source_character).toBe("aurelia");
    expect(parsed.motion.disposition).toBe("optional");
  });

  it("rejects unverified or uncommitted responses", () => {
    const unverified = validCharacterResponse();
    unverified.verified = false;
    expect(() => parseCharacterResponse(unverified)).toThrow(/verified and committed/);

    const uncommitted = validCharacterResponse();
    uncommitted.persistence_committed = false;
    expect(() => parseCharacterResponse(uncommitted)).toThrow(/verified and committed/);
  });

  it("rejects malformed semantic enums", () => {
    const value = validCharacterResponse();
    (value.motion as Record<string, unknown>).disposition = "required";
    expect(() => parseCharacterResponse(value)).toThrow(/disposition/);
  });

  it("rejects actuator fields recursively, including camelCase aliases", () => {
    const value = validCharacterResponse();
    (value.motion as Record<string, unknown>).details = {
      servoAngle: 90,
    };
    expect(() => parseCharacterResponse(value)).toThrow(/forbidden actuator-level fields/);
  });
});
