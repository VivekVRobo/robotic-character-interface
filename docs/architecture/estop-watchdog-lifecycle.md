# E-stop and watchdog lifecycle

PR-010 introduces the sticky lifecycle state that sits beside the static and dynamic motion checks.

## Safety rules

- The physical E-stop latches immediately.
- A software E-stop latches immediately.
- A watchdog heartbeat older than the configured timeout latches immediately.
- Invalid heartbeat age is treated as a watchdog safety fault.
- Releasing the physical E-stop does not clear the latch.
- Receiving a healthy heartbeat after a watchdog timeout does not clear the latch.
- The watchdog must be armed and healthy before a reset can succeed.
- V1 requires an explicit manual reset; automatic reset is rejected by configuration validation.
- A disarmed watchdog blocks motion even if no E-stop is currently latched.

The controller is deterministic and contains no background timer. The caller supplies heartbeat age from a monotonic clock. This keeps the lifecycle replayable in tests and lets the future `MotionSafetySupervisor` own the runtime timing boundary.

## Layering

```text
PR-008 static geometry/state eligibility
        ↓
PR-009 command/heartbeat freshness + rate limits
        ↓
PR-010 sticky E-stop/watchdog lifecycle
        ↓
PR-011 MotionSafetySupervisor
```

PR-010 still does **not** authorize an actuator command. A cleared lifecycle only removes one stop condition. Static and dynamic safety must also pass, and PR-011 will be the authoritative composition point.
