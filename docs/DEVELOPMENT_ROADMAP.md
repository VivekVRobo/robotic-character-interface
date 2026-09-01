# Development Roadmap

Build order is safety-first and vertical-slice driven.

1. **PR-001 Foundation** — monorepo, canonical docs, packaging, configs, CI skeletons.
2. **PR-002 Domain + Configuration** — typed enums/errors/settings and fail-closed validation.
3. **PR-003 Events** — typed bounded async event bus.
4. **PR-004 State Machine** — legal transitions and snapshots.
5. **PR-005 Health + Audit** — health registry and tamper-evident audit chain.
6. **PR-006 Protocol** — packet framing and Python/firmware golden vectors.
7. **PR-007 Mock Hardware** — fake glove/robot and abstract transports.
8. **PR-008..011 Safety Kernel** — joint/workspace/velocity/acceleration/freshness/watchdog/E-stop/supervisor.
9. **PR-012..014 Single Servo Slice** — robot firmware, gateway, HIL safety tests.
10. **PR-015..019 Robotics** — model, FK, IK, trajectory, controller.
11. **PR-020..022 Full Robot Firmware** — multi-joint driver, firmware safety, telemetry.
12. **PR-023..030 Gesture** — glove/radio, recorder, calibration/filtering/features/classifier/replay.
13. **PR-031..035 Character** — schemas, registry, Aurelia/Kanzaki, canon evaluation.
14. **PR-036..039 Cognition** — MeaningFrame/context/provider/structured output.
15. **PR-040..043 Behavior Embodiment** — primitives/styles/planner and character-specific motion tests.
16. **PR-044..048 Voice** — capture/VAD/STT/TTS/playback/barge-in/service.
17. **PR-049..051 Multimodal** — correlated gesture/voice/character/motion interactions.
18. **PR-052..055 API** — FastAPI, read-only status, controlled actions, WebSockets.
19. **PR-056..063 Frontend** — foundation, overview, gesture, robot, character, voice, safety, telemetry/experiments.
20. **PR-064..068 Fault Engineering** — injected failures and regression gates.
21. **PR-069..074 Benchmarks** — gesture/latency/character/IK/reliability/hardware measurements.
22. **PR-075..079 Hardening** — config, recovery, diagnostics, soak, security.
23. **PR-080..084 Evidence + RC** — docs, hardware evidence, reports, demos, v1.0.0-rc1.

## Release language

Before physical verification: **production-oriented architecture with simulation-validated software stack**.

After all hardware release gates pass: **production-ready**.
