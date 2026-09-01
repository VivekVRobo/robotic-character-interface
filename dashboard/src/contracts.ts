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

export type SpeechDelivery =
  | "neutral"
  | "supportive"
  | "confident"
  | "cautious"
  | "encouraging"
  | "empathetic";
export type ExpressionStrength = "none" | "subtle" | "moderate" | "strong";
export type MotionCue =
  | "none"
  | "listen"
  | "acknowledge"
  | "present"
  | "caution"
  | "celebrate"
  | "think";
export type MotionStyle = "restrained" | "standard" | "expressive";
export type MotionDisposition = "none" | "optional";

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
  source_character: "aurelia";
  speech: {
    text: string;
    delivery: SpeechDelivery;
    interruptible: boolean;
  };
  expression: {
    expression: string;
    strength: ExpressionStrength;
  };
  motion: {
    cue: MotionCue;
    style: MotionStyle;
    disposition: MotionDisposition;
  };
  verified: true;
  persistence_committed: true;
  persistence_durable: boolean;
}

const CONNECTION_STATES = new Set<ConnectionState>([
  "disconnected",
  "connecting",
  "connected",
  "error",
]);
const SYSTEM_STATES = new Set<SystemState>([
  "BOOT",
  "SELF_TEST",
  "CALIBRATING",
  "IDLE",
  "ARMED",
  "EXECUTING",
  "DEGRADED",
  "FAULT",
  "ESTOP",
  "SHUTDOWN",
]);
const SPEECH_DELIVERIES = new Set<SpeechDelivery>([
  "neutral",
  "supportive",
  "confident",
  "cautious",
  "encouraging",
  "empathetic",
]);
const EXPRESSION_STRENGTHS = new Set<ExpressionStrength>([
  "none",
  "subtle",
  "moderate",
  "strong",
]);
const MOTION_CUES = new Set<MotionCue>([
  "none",
  "listen",
  "acknowledge",
  "present",
  "caution",
  "celebrate",
  "think",
]);
const MOTION_STYLES = new Set<MotionStyle>(["restrained", "standard", "expressive"]);
const MOTION_DISPOSITIONS = new Set<MotionDisposition>(["none", "optional"]);

const FORBIDDEN_ACTUATOR_KEYS = new Set([
  "servo",
  "servoangle",
  "servoangles",
  "pwm",
  "pulsewidth",
  "pulsewidthus",
  "jointtarget",
  "jointtargets",
  "trajectory",
  "motorcommand",
  "motorcommands",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizedKey(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function hasForbiddenActuatorKey(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.some(hasForbiddenActuatorKey);
  }
  if (!isRecord(value)) {
    return false;
  }
  return Object.entries(value).some(([key, child]) => {
    return FORBIDDEN_ACTUATOR_KEYS.has(normalizedKey(key)) || hasForbiddenActuatorKey(child);
  });
}

function requireString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${key} must be a non-empty string`);
  }
  return value;
}

function requireBoolean(record: Record<string, unknown>, key: string): boolean {
  const value = record[key];
  if (typeof value !== "boolean") {
    throw new Error(`${key} must be boolean`);
  }
  return value;
}

function nullableNonNegativeInteger(
  record: Record<string, unknown>,
  key: string,
  maximum = Number.MAX_SAFE_INTEGER,
): number | null {
  const value = record[key];
  if (value === null) {
    return null;
  }
  if (
    typeof value !== "number" ||
    !Number.isSafeInteger(value) ||
    value < 0 ||
    value > maximum
  ) {
    throw new Error(`${key} must be null or a non-negative safe integer`);
  }
  return value;
}

function requireEnum<T extends string>(
  record: Record<string, unknown>,
  key: string,
  allowed: ReadonlySet<T>,
): T {
  const value = record[key];
  if (typeof value !== "string" || !allowed.has(value as T)) {
    throw new Error(`${key} has an unsupported value`);
  }
  return value as T;
}

export function parseDashboardSnapshot(value: unknown): DashboardSnapshot {
  if (!isRecord(value)) {
    throw new Error("Dashboard snapshot must be an object");
  }
  const telemetry = value.telemetry;
  if (!isRecord(telemetry)) {
    throw new Error("telemetry must be an object");
  }

  const connection = requireEnum(value, "connection", CONNECTION_STATES);
  const systemState = requireEnum(value, "systemState", SYSTEM_STATES);
  const estopLatched = requireBoolean(value, "estopLatched");
  const heartbeatHealthy = requireBoolean(value, "heartbeatHealthy");

  if (connection !== "connected" && heartbeatHealthy) {
    throw new Error("heartbeat cannot be healthy while runtime is not connected");
  }
  if (systemState === "ESTOP" && !estopLatched) {
    throw new Error("ESTOP system state requires a latched E-stop");
  }

  const gatewayError = value.gatewayError;
  if (gatewayError !== null && (typeof gatewayError !== "string" || gatewayError.trim() === "")) {
    throw new Error("gatewayError must be null or a non-empty string");
  }

  return {
    connection,
    systemState,
    estopLatched,
    heartbeatHealthy,
    gatewayError,
    telemetry: {
      lastFrameSequence: nullableNonNegativeInteger(telemetry, "lastFrameSequence", 0xffff),
      heartbeatAgeMs: nullableNonNegativeInteger(telemetry, "heartbeatAgeMs"),
      sentCount: nullableNonNegativeInteger(telemetry, "sentCount"),
      acknowledgedCount: nullableNonNegativeInteger(telemetry, "acknowledgedCount"),
      rejectedCount: nullableNonNegativeInteger(telemetry, "rejectedCount"),
    },
  };
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
      delivery: requireEnum(speech, "delivery", SPEECH_DELIVERIES),
      interruptible: speech.interruptible,
    },
    expression: {
      expression: requireString(expression, "expression"),
      strength: requireEnum(expression, "strength", EXPRESSION_STRENGTHS),
    },
    motion: {
      cue: requireEnum(motion, "cue", MOTION_CUES),
      style: requireEnum(motion, "style", MOTION_STYLES),
      disposition: requireEnum(motion, "disposition", MOTION_DISPOSITIONS),
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
