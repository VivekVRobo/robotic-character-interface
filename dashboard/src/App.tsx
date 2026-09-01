import {
  type CharacterResponseV1,
  type DashboardSnapshot,
  EMPTY_DASHBOARD_SNAPSHOT,
} from "./contracts";

export interface AppProps {
  snapshot?: DashboardSnapshot;
  characterResponse?: CharacterResponseV1 | null;
  onReconnect?: () => void;
}

function valueOrUnavailable(value: number | null, suffix = ""): string {
  return value === null ? "Unavailable" : `${value}${suffix}`;
}

function statusLabel(snapshot: DashboardSnapshot): string {
  if (snapshot.estopLatched || snapshot.systemState === "ESTOP") {
    return "EMERGENCY STOP LATCHED";
  }
  if (snapshot.connection === "error") {
    return "Connection error";
  }
  if (snapshot.connection !== "connected") {
    return "Runtime disconnected";
  }
  return snapshot.heartbeatHealthy ? "Runtime connected" : "Heartbeat unhealthy";
}

export function App({
  snapshot = EMPTY_DASHBOARD_SNAPSHOT,
  characterResponse = null,
  onReconnect,
}: AppProps) {
  const estopActive = snapshot.estopLatched || snapshot.systemState === "ESTOP";

  return (
    <main>
      <header>
        <h1>Robotic Character Interface</h1>
        <p>Safety-governed runtime dashboard</p>
      </header>

      <section aria-labelledby="runtime-status-heading">
        <h2 id="runtime-status-heading">Runtime status</h2>
        <p role="status">{statusLabel(snapshot)}</p>
        <dl>
          <div>
            <dt>Connection</dt>
            <dd>{snapshot.connection}</dd>
          </div>
          <div>
            <dt>System state</dt>
            <dd>{snapshot.systemState}</dd>
          </div>
          <div>
            <dt>Heartbeat</dt>
            <dd>{snapshot.heartbeatHealthy ? "Healthy" : "Not healthy"}</dd>
          </div>
        </dl>
        {snapshot.connection !== "connected" && onReconnect ? (
          <button type="button" onClick={onReconnect}>
            Reconnect runtime
          </button>
        ) : null}
      </section>

      <section aria-labelledby="safety-heading">
        <h2 id="safety-heading">Safety</h2>
        <p role={estopActive ? "alert" : undefined}>
          {estopActive ? "EMERGENCY STOP LATCHED — manual reset required" : "E-stop not latched"}
        </p>
        <p>
          Motion authorization: {snapshot.systemState === "ARMED" && !estopActive
            ? "Runtime may evaluate candidates through MotionSafetySupervisor"
            : "Not eligible from current dashboard state"}
        </p>
      </section>

      <section aria-labelledby="gateway-heading">
        <h2 id="gateway-heading">Robot gateway</h2>
        {snapshot.gatewayError ? <p role="alert">Gateway error: {snapshot.gatewayError}</p> : null}
        <dl>
          <div>
            <dt>Last frame sequence</dt>
            <dd>{valueOrUnavailable(snapshot.telemetry.lastFrameSequence)}</dd>
          </div>
          <div>
            <dt>Heartbeat age</dt>
            <dd>{valueOrUnavailable(snapshot.telemetry.heartbeatAgeMs, " ms")}</dd>
          </div>
          <div>
            <dt>Sent</dt>
            <dd>{valueOrUnavailable(snapshot.telemetry.sentCount)}</dd>
          </div>
          <div>
            <dt>Acknowledged</dt>
            <dd>{valueOrUnavailable(snapshot.telemetry.acknowledgedCount)}</dd>
          </div>
          <div>
            <dt>Rejected</dt>
            <dd>{valueOrUnavailable(snapshot.telemetry.rejectedCount)}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="character-heading">
        <h2 id="character-heading">Character response</h2>
        {characterResponse ? (
          <article>
            <p>
              <strong>{characterResponse.source_character}</strong>: {characterResponse.speech.text}
            </p>
            <dl>
              <div>
                <dt>Expression</dt>
                <dd>{characterResponse.expression.expression}</dd>
              </div>
              <div>
                <dt>Speech delivery</dt>
                <dd>{characterResponse.speech.delivery}</dd>
              </div>
              <div>
                <dt>Motion cue</dt>
                <dd>
                  {characterResponse.motion.cue} ({characterResponse.motion.disposition})
                </dd>
              </div>
              <div>
                <dt>Persistence</dt>
                <dd>{characterResponse.persistence_durable ? "Durable" : "Committed, non-durable"}</dd>
              </div>
            </dl>
            <p>Semantic intent only — physical motion remains subject to deterministic safety.</p>
          </article>
        ) : (
          <p>No verified CharacterResponse received.</p>
        )}
      </section>
    </main>
  );
}
