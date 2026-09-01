export const CHARACTER_RESPONSE_SCHEMA = "rci.character_response.v1" as const;

export type ConnectionState = "disconnected" | "connecting" | "connected" | "error";
export type SystemState =
  | "BOOT"
  | "SELF_TEST"
  | "CALIBRATING"
  | "IDLE"
  | "ARMED"
  | "EXECUTING"
  | "DEGRADED"
  | "FAULT"
  | "ESTOP"
  | "SHUTDOWN";

export interface DashboardSnapshot {
  connection: ConnectionState;
  systemState: SystemState;
  estopLatched: boolean;
  heartbeatHealthy: boolean;
  gatewayError: string | null;
  telemetry: {
    lastFrameSequence: number | null;
    heartbeatAgeMs: number | null;
    sentCount: number | null;
    acknowledgedCount: number | null;
    rejectedCount: number | null;
  };
}

export interface CharacterResponseV1 {
  schema_version: typeof CHARACTER_RESPONSE_SCHEMA;
  interaction_id: string;
  decision_id: string;
  source_character: string;
  speech: {
    text: string;
    delivery: string;
    interruptible: boolean;
  };
  expression: {
    expression: string;
    strength: string;
  };
  motion: {
    cue: string;
    style: string;
    disposition: "none" | "optional";
  };
  verified: true;
  persistence_committed: true;
  persistence_durable: boolean;
}

const FORBIDDEN_ACTUATOR_KEYS = new Set([
  "servo",
  "servo_angle",
  "servo_angles",
  "pwm",
  "pulse_width",
  "pulse_width_us",
  "joint_target",
  "joint_targets",
  "trajectory",
  "motor_command",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasForbiddenActuatorKey(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.some(hasForbiddenActuatorKey);
  }
  if (!isRecord(value)) {
    return false;
  }
  return Object.entries(value).some(([key, child]) => {
    const normalized = key.toLowerCase();
    return FORBIDDEN_ACTUATOR_KEYS.has(normalized) || hasForbiddenActuatorKey(child);
  });
}

function requireString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${key} must be a non-empty string`);
  }
  return value;
}

export function parseCharacterResponse(value: unknown): CharacterResponseV1 {
  if (!isRecord(value)) {
    throw new Error("CharacterResponse must be an object");
  }
  if (hasForbiddenActuatorKey(value)) {
    throw new Error("CharacterResponse contains forbidden actuator-level fields");
  }
  if (value.schema_version !== CHARACTER_RESPONSE_SCHEMA) {
    throw new Error("Unsupported CharacterResponse schema");
  }
  if (value.source_character !== "aurelia") {
    throw new Error("CharacterResponse source must be aurelia");
  }
  if (value.verified !== true || value.persistence_committed !== true) {
    throw new Error("CharacterResponse must be verified and committed");
  }

  const speech = value.speech;
  const expression = value.expression;
  const motion = value.motion;
  if (!isRecord(speech) || !isRecord(expression) || !isRecord(motion)) {
    throw new Error("CharacterResponse intents must be objects");
  }
  const disposition = motion.disposition;
  if (disposition !== "none" && disposition !== "optional") {
    throw new Error("Character motion disposition must be none or optional");
  }
  if (typeof speech.interruptible !== "boolean") {
    throw new Error("speech.interruptible must be boolean");
  }
  if (typeof value.persistence_durable !== "boolean") {
    throw new Error("persistence_durable must be boolean");
  }

  return {
    schema_version: CHARACTER_RESPONSE_SCHEMA,
    interaction_id: requireString(value, "interaction_id"),
    decision_id: requireString(value, "decision_id"),
    source_character: "aurelia",
    speech: {
      text: requireString(speech, "text"),
      delivery: requireString(speech, "delivery"),
      interruptible: speech.interruptible,
    },
    expression: {
      expression: requireString(expression, "expression"),
      strength: requireString(expression, "strength"),
    },
    motion: {
      cue: requireString(motion, "cue"),
      style: requireString(motion, "style"),
      disposition,
    },
    verified: true,
    persistence_committed: true,
    persistence_durable: value.persistence_durable,
  };
}

export const EMPTY_DASHBOARD_SNAPSHOT: DashboardSnapshot = Object.freeze({
  connection: "disconnected",
  systemState: "BOOT",
  estopLatched: false,
  heartbeatHealthy: false,
  gatewayError: null,
  telemetry: Object.freeze({
    lastFrameSequence: null,
    heartbeatAgeMs: null,
    sentCount: null,
    acknowledgedCount: null,
    rejectedCount: null,
  }),
});
