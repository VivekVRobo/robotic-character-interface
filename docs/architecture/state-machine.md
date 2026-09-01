# Runtime State Machine

The authoritative state is an immutable `StateSnapshot` owned by `StateManager`. Subsystem state is replaced atomically and increments a global revision. System lifecycle state can only change through the canonical transition table.

## Nominal path

`BOOT -> SELF_TEST -> CALIBRATING -> IDLE -> ARMED -> EXECUTING`

Execution normally returns to `ARMED`; disarming returns `ARMED -> IDLE`.

## Exceptional states

- `DEGRADED`: service remains partially functional but unrestricted progression is blocked.
- `FAULT`: recovery must restart at `SELF_TEST` or shut down.
- `ESTOP`: recovery must restart at `SELF_TEST` after the independent E-stop reset procedure, or shut down.
- `SHUTDOWN`: terminal state for the running process.

Same-state transitions are not silently accepted; callers must decide whether an operation should be idempotent before requesting a transition.

## State/event consistency

A system transition updates the authoritative snapshot and publishes a `SystemStateChanged` event while holding the state transaction. If publication fails, the snapshot rolls back. FAULT and ESTOP transition events are published at critical priority.
