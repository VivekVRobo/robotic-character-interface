# Robotic Character Interface

A safety-governed multimodal AI character embodiment robotics platform that translates human gesture, voice, conversational context, and character personality into deterministic, safety-validated physical robotic behavior.

## Status

**Foundation / simulation-first implementation.** Hardware-specific claims remain unverified until measured on the physical system.

## Core invariant

No AI, character, gesture, API, or frontend component may directly control actuators. Physical motion must pass through the behavior layer, trajectory planner, deterministic Motion Safety Supervisor, Robot Gateway, MCU validation, and servo driver.

## Repository map

- `src/rci/` — Python backend and domain logic
- `dashboard/` — React + TypeScript operator/diagnostic UI
- `firmware/` — glove, gateway, robot MCU firmware
- `characters/` — character canon, voice, motion, evaluations
- `configs/` — validated runtime configuration
- `schemas/` — protocol and data contracts
- `tests/` — unit, integration, simulation, contract, safety, fault, HIL, E2E
- `datasets/` — gesture/session data
- `benchmarks/` — reproducible engineering results
- `hardware/` — BOM, wiring, mechanics, calibration evidence
- `docs/` — canonical architecture and engineering documentation

Start with `docs/MASTER_ARCHITECTURE.md`, `docs/REPO_IMPLEMENTATION_PLAN.md`, and `docs/DEVELOPMENT_ROADMAP.md`.
