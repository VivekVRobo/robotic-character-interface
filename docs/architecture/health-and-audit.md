# Health and Audit Architecture

## Health

Subsystems expose asynchronous health providers. `HealthRegistry` runs checks concurrently and converts provider exceptions into FAILED component results rather than allowing a monitor crash. A failed critical component produces overall `FAILED`; noncritical failures, degraded states, or unknown states produce overall `DEGRADED`. An empty registry is `UNKNOWN`, never optimistically healthy.

`HealthMonitor` publishes `HealthChanged` only on transitions. First observation is a transition from `UNKNOWN`. Critical failures are emitted at critical event priority.

## Audit

The audit log is **append-only by application contract and tamper-evident**, not physically immutable storage. Every entry includes a monotonically increasing sequence, previous-entry hash, and SHA-256 hash over a canonical JSON representation of its fields. The chain is verified on load and can be verified on demand.

`EventAuditBridge` can subscribe to the base runtime `Event` type and append all emitted events. Durable mode writes JSONL, flushes, and calls `fsync` before accepting the record into the in-memory chain. If persistence fails, the event handler fails visibly through the event bus failure accounting rather than pretending the event was audited.
