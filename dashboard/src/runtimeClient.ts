import {
  type CharacterResponseV1,
  type DashboardSnapshot,
  parseCharacterResponse,
  parseDashboardSnapshot,
} from "./contracts";

export interface RobotJointTelemetryView {
  jointId: number;
  positionCdeg: number;
  velocityCdegS: number;
  currentMa: number;
}

export interface RobotTelemetryView {
  uptimeMs: number;
  systemState: DashboardSnapshot["systemState"];
  supplyMv: number;
  joints: RobotJointTelemetryView[];
  simulationOnly: true;
  measuredHardware: false;
}

export interface InteractionView {
  characterResponse: CharacterResponseV1;
  simulationExecuted: boolean;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireInteger(
  record: Record<string, unknown>,
  key: string,
  minimum = 0,
  maximum = Number.MAX_SAFE_INTEGER,
): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < minimum || value > maximum) {
    throw new Error(`${key} must be an integer in [${minimum}, ${maximum}]`);
  }
  return value;
}

export function parseRobotTelemetry(value: unknown): RobotTelemetryView {
  if (!isRecord(value) || !Array.isArray(value.joints)) {
    throw new Error("Robot telemetry must contain a joints array");
  }
  if (value.simulationOnly !== true || value.measuredHardware !== false) {
    throw new Error("Robot telemetry provenance must remain simulation-only");
  }

  const stateCarrier = parseDashboardSnapshot({
    connection: "connected",
    systemState: value.systemState,
    estopLatched: value.systemState === "ESTOP",
    heartbeatHealthy: false,
    gatewayError: null,
    telemetry: {
      lastFrameSequence: null,
      heartbeatAgeMs: null,
      sentCount: null,
      acknowledgedCount: null,
      rejectedCount: null,
    },
  });

  const joints = value.joints.map((item) => {
    if (!isRecord(item)) {
      throw new Error("Robot joint telemetry must be an object");
    }
    return {
      jointId: requireInteger(item, "jointId", 1, 255),
      positionCdeg: requireInteger(item, "positionCdeg", -32768, 32767),
      velocityCdegS: requireInteger(item, "velocityCdegS", -32768, 32767),
      currentMa: requireInteger(item, "currentMa", 0, 65535),
    };
  });
  if (new Set(joints.map((joint) => joint.jointId)).size !== joints.length) {
    throw new Error("Robot telemetry contains duplicate joint IDs");
  }

  return {
    uptimeMs: requireInteger(value, "uptimeMs", 0, 0xffffffff),
    systemState: stateCarrier.systemState,
    supplyMv: requireInteger(value, "supplyMv", 0, 65535),
    joints,
    simulationOnly: true,
    measuredHardware: false,
  };
}

export async function fetchDashboardSnapshot(): Promise<DashboardSnapshot> {
  const response = await fetch("/api/dashboard/snapshot");
  if (!response.ok) {
    throw new Error(`Dashboard snapshot failed with HTTP ${response.status}`);
  }
  return parseDashboardSnapshot(await response.json());
}

export async function sendTextInteraction(text: string): Promise<InteractionView> {
  const normalized = text.trim();
  if (!normalized) {
    throw new Error("Interaction text cannot be empty");
  }
  const response = await fetch("/api/simulation/interact", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      simulation: true,
      timestamp_ms: Date.now(),
      text: normalized,
    }),
  });
  if (!response.ok) {
    throw new Error(`Interaction failed with HTTP ${response.status}`);
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload)) {
    throw new Error("Interaction response must be an object");
  }
  return {
    characterResponse: parseCharacterResponse(payload.character_response),
    simulationExecuted: payload.simulation_execution !== null,
  };
}

export function createTelemetrySocket(
  onSnapshot: (snapshot: DashboardSnapshot, telemetry: RobotTelemetryView) => void,
  onError: (message: string) => void,
): WebSocket {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${scheme}//${window.location.host}/ws/telemetry`);
  socket.addEventListener("message", (event) => {
    try {
      const payload: unknown = JSON.parse(String(event.data));
      if (!isRecord(payload)) {
        throw new Error("Telemetry WebSocket payload must be an object");
      }
      onSnapshot(
        parseDashboardSnapshot(payload.dashboard),
        parseRobotTelemetry(payload.robotTelemetry),
      );
    } catch (error) {
      onError(error instanceof Error ? error.message : "Invalid telemetry payload");
    }
  });
  socket.addEventListener("error", () => onError("Telemetry WebSocket connection failed"));
  return socket;
}
