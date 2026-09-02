import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LiveDashboard } from "./LiveDashboard";
import type { CharacterResponseV1, DashboardSnapshot } from "./contracts";
import type { RobotTelemetryView } from "./runtimeClient";

const mocks = vi.hoisted(() => ({
  fetchDashboardSnapshot: vi.fn(),
  createTelemetrySocket: vi.fn(),
  sendTextInteraction: vi.fn(),
}));

vi.mock("./runtimeClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./runtimeClient")>();
  return {
    ...actual,
    fetchDashboardSnapshot: mocks.fetchDashboardSnapshot,
    createTelemetrySocket: mocks.createTelemetrySocket,
    sendTextInteraction: mocks.sendTextInteraction,
  };
});

const snapshot: DashboardSnapshot = {
  connection: "connected",
  systemState: "IDLE",
  estopLatched: false,
  heartbeatHealthy: true,
  gatewayError: null,
  telemetry: {
    lastFrameSequence: 4,
    heartbeatAgeMs: 0,
    sentCount: 5,
    acknowledgedCount: 5,
    rejectedCount: 0,
  },
};

const telemetry: RobotTelemetryView = {
  uptimeMs: 1000,
  systemState: "IDLE",
  supplyMv: 6000,
  simulationOnly: true,
  measuredHardware: false,
  joints: [{ jointId: 1, positionCdeg: 1000, velocityCdegS: 0, currentMa: 80 }],
};

const character: CharacterResponseV1 = {
  schema_version: "rci.character_response.v1",
  interaction_id: "interaction_1",
  decision_id: "decision_1",
  source_character: "aurelia",
  speech: { text: "Simulation response.", delivery: "neutral", interruptible: true },
  expression: { expression: "neutral", strength: "subtle" },
  motion: { cue: "present", style: "restrained", disposition: "optional" },
  verified: true,
  persistence_committed: true,
  persistence_durable: false,
};

beforeEach(() => {
  mocks.fetchDashboardSnapshot.mockReset();
  mocks.createTelemetrySocket.mockReset();
  mocks.sendTextInteraction.mockReset();
  mocks.fetchDashboardSnapshot.mockResolvedValue(snapshot);
  mocks.createTelemetrySocket.mockImplementation((onSnapshot: (s: DashboardSnapshot, t: RobotTelemetryView) => void) => {
    queueMicrotask(() => onSnapshot(snapshot, telemetry));
    return { close: vi.fn() } as unknown as WebSocket;
  });
});

describe("LiveDashboard", () => {
  it("renders live simulation telemetry with explicit non-physical provenance", async () => {
    render(<LiveDashboard />);

    expect(await screen.findByText("Runtime connected")).toBeTruthy();
    expect(await screen.findByText(/Simulation-only telemetry/)).toBeTruthy();
    expect(screen.getByText("10.00°")).toBeTruthy();
    expect(screen.getByText(/not measured physical hardware/)).toBeTruthy();
  });

  it("sends high-level text interaction and renders the verified character response", async () => {
    mocks.sendTextInteraction.mockResolvedValue({
      characterResponse: character,
      simulationExecuted: true,
    });
    render(<LiveDashboard />);

    const input = screen.getByLabelText("Message to Aurelia");
    fireEvent.change(input, { target: { value: "Present the result" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => expect(mocks.sendTextInteraction).toHaveBeenCalledWith("Present the result"));
    expect(await screen.findByText(/Simulation response/)).toBeTruthy();
    expect(screen.getByText(/digital twin only/)).toBeTruthy();
  });

  it("surfaces runtime connection errors rather than inventing telemetry", async () => {
    mocks.fetchDashboardSnapshot.mockRejectedValue(new Error("runtime unavailable"));
    mocks.createTelemetrySocket.mockImplementation(() => ({ close: vi.fn() }) as unknown as WebSocket);
    render(<LiveDashboard />);

    expect(await screen.findByText("Connection error")).toBeTruthy();
    expect(screen.getByText(/runtime unavailable/)).toBeTruthy();
    expect(screen.getByText("Digital twin telemetry unavailable.")).toBeTruthy();
  });
});
