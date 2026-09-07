# V006 Deterministic Motion-Safety Evidence

V006 turns the production digital-twin safety path into a machine-readable CI artifact. It complements the existing V005 cross-repository adversarial campaign rather than replacing it.

## Path under test

```text
SimulationBehaviorEmbodimentPlanner
  -> RobotController
  -> production RobotModel / reference simulation profile
  -> MotionCandidate + MotionDynamics
  -> MotionSafetySupervisor
  -> MotionDecision / MotionAuthorization
```

The campaign starts from one valid production-model motion and challenges the supervisor with isolated faults. A fresh supervisor is constructed for every case so lifecycle state from one challenge cannot contaminate another.

## Deterministic cases

| Case | Expected outcome |
| --- | --- |
| baseline authorization | `APPROVE`, no violations, authorization minted |
| state not allowed | `REJECT` / `STATE_NOT_ALLOWED` |
| physical E-stop active | `ESTOP` / `LIFECYCLE_ESTOP_LATCHED` |
| joint limit violation | `REJECT` / `JOINT_LIMIT_VIOLATION` |
| workspace limit violation | `REJECT` / `WORKSPACE_LIMIT_VIOLATION` |
| stale command | `REJECT` / `COMMAND_STALE` |
| stale heartbeat | `ESTOP` / `LIFECYCLE_ESTOP_LATCHED` |
| velocity limit violation | `REJECT` / `VELOCITY_LIMIT_VIOLATION` |
| acceleration limit violation | `REJECT` / `ACCELERATION_LIMIT_VIOLATION` |

Run locally:

```bash
python tools/run_safety_evidence.py --output reports/simulation/local-safety-evidence.json
```

Safety and Contract CI runs the same command and uploads `rci-motion-safety-evidence`.

## Provenance and claim boundary

The JSON report records:

```text
evidence_type: deterministic_software_safety_campaign
simulation_only: true
hardware_verified: false
physical_motion: false
```

It also includes a canonical SHA-256 digest over the report contents before the digest field is added.

A green V006 gate proves that the current software safety composition produces the expected deterministic decisions for the listed digital-twin challenge cases. It does **not** prove real E-stop wiring, real watchdog timing, measured joint/workspace limits, servo accuracy, current/voltage behavior, collision safety, or physical robot motion.

Those remain hardware/HIL evidence gates.
