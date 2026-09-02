import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { App } from "./App";
import {
  type CharacterResponseV1,
  type DashboardSnapshot,
  EMPTY_DASHBOARD_SNAPSHOT,
} from "./contracts";
import {
  createTelemetrySocket,
  fetchDashboardSnapshot,
  type RobotTelemetryView,
  sendTextInteraction,
} from "./runtimeClient";

function connectionError(message: string): DashboardSnapshot {
  return {
    ...EMPTY_DASHBOARD_SNAPSHOT,
    connection: "error",
    gatewayError: message,
  };
}

export function LiveDashboard() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>({
    ...EMPTY_DASHBOARD_SNAPSHOT,
    connection: "connecting",
  });
  const [characterResponse, setCharacterResponse] = useState<CharacterResponseV1 | null>(null);
  const [robotTelemetry, setRobotTelemetry] = useState<RobotTelemetryView | null>(null);
  const [text, setText] = useState("");
  const [interactionError, setInteractionError] = useState<string | null>(null);
  const [simulationExecuted, setSimulationExecuted] = useState(false);
  const [sending, setSending] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    socketRef.current?.close();
    setSnapshot((current) => ({ ...current, connection: "connecting", gatewayError: null }));

    void fetchDashboardSnapshot()
      .then(setSnapshot)
      .catch((error: unknown) => {
        setSnapshot(connectionError(error instanceof Error ? error.message : "Snapshot failed"));
      });

    socketRef.current = createTelemetrySocket(
      (nextSnapshot, telemetry) => {
        setSnapshot(nextSnapshot);
        setRobotTelemetry(telemetry);
      },
      (message) => setSnapshot(connectionError(message)),
    );
  }, []);

  useEffect(() => {
    connect();
    return () => socketRef.current?.close();
  }, [connect]);

  async function submitInteraction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setInteractionError(null);
    try {
      const result = await sendTextInteraction(text);
      setCharacterResponse(result.characterResponse);
      setSimulationExecuted(result.simulationExecuted);
      setText("");
    } catch (error) {
      setInteractionError(error instanceof Error ? error.message : "Interaction failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <section aria-labelledby="interaction-heading">
        <h2 id="interaction-heading">Simulation interaction</h2>
        <form onSubmit={submitInteraction}>
          <label htmlFor="interaction-text">Message to Aurelia</label>
          <input
            id="interaction-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Ask Aurelia something…"
          />
          <button type="submit" disabled={sending || text.trim() === ""}>
            {sending ? "Sending…" : "Send"}
          </button>
        </form>
        {interactionError ? <p role="alert">{interactionError}</p> : null}
        {simulationExecuted ? (
          <p role="status">Semantic behavior executed in the digital twin only.</p>
        ) : null}
      </section>

      <App snapshot={snapshot} characterResponse={characterResponse} onReconnect={connect} />

      <section aria-labelledby="digital-twin-heading">
        <h2 id="digital-twin-heading">Digital twin telemetry</h2>
        {robotTelemetry ? (
          <>
            <p>
              Simulation-only telemetry — supply {robotTelemetry.supplyMv} mV, state {robotTelemetry.systemState}
            </p>
            <table>
              <thead>
                <tr>
                  <th>Joint</th>
                  <th>Position</th>
                  <th>Velocity</th>
                  <th>Current</th>
                </tr>
              </thead>
              <tbody>
                {robotTelemetry.joints.map((joint) => (
                  <tr key={joint.jointId}>
                    <td>{joint.jointId}</td>
                    <td>{(joint.positionCdeg / 100).toFixed(2)}°</td>
                    <td>{(joint.velocityCdegS / 100).toFixed(2)}°/s</td>
                    <td>{joint.currentMa} mA</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p>These values are simulated predictions, not measured physical hardware.</p>
          </>
        ) : (
          <p>Digital twin telemetry unavailable.</p>
        )}
      </section>
    </>
  );
}
