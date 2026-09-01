# Safety Model

## Independent layers

1. Host state/arming rules
2. Motion Safety Supervisor
3. Robot Gateway typed validated-command boundary
4. MCU packet/TTL/joint/heartbeat validation
5. Software stop
6. Physical E-stop removing actuator power

## Fail-safe defaults

Unknown health, stale telemetry, expired commands, illegal runtime states, invalid configuration, missing heartbeat, and active E-stop all block new motion.

## V1 policy

Unsafe commands are rejected rather than silently clamped unless a clamp behavior is specifically documented and tested.
