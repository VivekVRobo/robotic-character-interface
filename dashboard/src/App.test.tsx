import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { App } from "./App";
import type { CharacterResponseV1, DashboardSnapshot } from "./contracts";

afterEach(cleanup);

function snapshot(overrides: Partial<DashboardSnapshot> = {}): DashboardSnapshot {
  return {
    connection: "connected",
    systemState: "IDLE",
    estopLatched: false,
    heartbeatHealthy: true,
    gatewayError: null,
    telemetry: {
      lastFrameSequence: 12,
      heartbeatAgeMs: 40,
      sentCount: 9,
      acknowledgedCount: 8,
      rejectedCount: 1,
    },
    ...overrides,
  };
}

function characterResponse(): CharacterResponseV1 {
  return {
    schema_version: "rci.character_response.v1",
    interaction_id: "interaction-1",
    decision_id: "decision-1",
    source_character: "aurelia",
    speech: {
      text: "I can present the verified plan.",
      delivery: "confident",
      interruptible: true,
    },
    expression: {
      expression: "confident",
      strength: "subtle",
    },
    motion: {
      cue: "present",
      style: "restrained",
      disposition: "optional",
    },
    verified: true,
    persistence_committed: true,
    persistence_durable: true,
  };
}

describe("RCI operational dashboard", () => {
  it("renders a truthful disconnected BOOT state with unavailable telemetry", () => {
    render(<App />);

    expect(screen.getByText("Runtime disconnected")).toBeTruthy();
    expect(screen.getByText("BOOT")).toBeTruthy();
    expect(screen.getAllByText("Unavailable").length).toBe(5);
    expect(screen.getByText("No verified CharacterResponse received.")).toBeTruthy();
  });

  it("offers reconnect when disconnected and invokes the supplied action", () => {
    const onReconnect = vi.fn();
    render(<App onReconnect={onReconnect} />);

    fireEvent.click(screen.getByRole("button", { name: "Reconnect runtime" }));
    expect(onReconnect).toHaveBeenCalledTimes(1);
  });

  it("shows ARMED as eligible only for deterministic supervisor evaluation", () => {
    render(<App snapshot={snapshot({ systemState: "ARMED" })} />);

    expect(screen.getByText("Runtime connected")).toBeTruthy();
    expect(
      screen.getByText(
        /Runtime may evaluate candidates through MotionSafetySupervisor/,
      ),
    ).toBeTruthy();
  });

  it("surfaces a latched E-stop as an alert and blocks dashboard eligibility", () => {
    render(
      <App
        snapshot={snapshot({
          systemState: "ESTOP",
          estopLatched: true,
          heartbeatHealthy: false,
        })}
      />,
    );

    expect(screen.getByRole("alert").textContent).toContain("manual reset required");
    expect(screen.getByText(/Not eligible from current dashboard state/)).toBeTruthy();
  });

  it("surfaces RobotGateway failure without inventing telemetry", () => {
    render(
      <App
        snapshot={snapshot({
          gatewayError: "ACK timeout",
          telemetry: {
            lastFrameSequence: null,
            heartbeatAgeMs: null,
            sentCount: null,
            acknowledgedCount: null,
            rejectedCount: null,
          },
        })}
      />,
    );

    expect(screen.getByRole("alert").textContent).toContain("ACK timeout");
    expect(screen.getAllByText("Unavailable").length).toBe(5);
  });

  it("renders verified CharacterResponse semantics without implying physical authorization", () => {
    render(<App snapshot={snapshot()} characterResponse={characterResponse()} />);

    expect(
      screen.getByText((_, element) =>
        element?.tagName === "P" &&
        element.textContent?.includes("I can present the verified plan.") === true,
      ),
    ).toBeTruthy();
    expect(
      screen.getByText((_, element) =>
        element?.tagName === "DD" &&
        element.textContent?.replace(/\s+/g, " ").trim() === "present (optional)",
      ),
    ).toBeTruthy();
    expect(screen.getByText("Durable")).toBeTruthy();
    expect(
      screen.getByText(/physical motion remains subject to deterministic safety/i),
    ).toBeTruthy();
  });
});
