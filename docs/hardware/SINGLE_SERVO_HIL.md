# PR-014 — Single-Servo Hardware-in-the-Loop Gate

## Status

This milestone prepares the first physical servo experiment. It does **not** claim that a servo has moved, that the PCA9685 output has been measured, or that any production joint limit is verified.

The canonical `configs/servos.yaml` remains globally unverified. PR-014 creates a separate, one-servo HIL permit so a carefully measured bench experiment can happen without falsely declaring the full actuator bank ready.

## Safety invariant

A single-servo HIL permit is readiness evidence only. Normal application code cannot consume it and normal `robot.ino` does not include the HIL guard. The firmware HIL guard ends at `kEligibleForDriverLayer` and contains no PWM/servo write API.

## Evidence required before energizing one servo

Record all values from the actual bench setup; do not copy nominal internet specifications into the evidence file.

### Identity and calibration

- exact joint name, channel, and protocol ID
- actual servo model fitted on the bench
- actual driver used
- actual configured PWM frequency
- measured lower, neutral, and upper angles
- measured pulse widths corresponding to those three points
- deliberately narrower first-test lower/upper angles
- maximum allowed first-test step size

The first-test envelope must lie inside the measured range and contain neutral. The software accepts reversed pulse direction, but the neutral pulse must lie between the two measured pulse endpoints.

### Electrical verification

- measured actuator supply voltage
- measured logic supply voltage
- configured current limit
- common ground verified
- actuator and logic rails separated
- independent E-stop physically tested
- power-cut behavior physically tested

### Mechanical verification

- servo physically secured
- load path clear
- manual range checked with power removed
- hard-stop clearance verified

### Evidence artifacts

At minimum include:

- one wiring artifact
- one measurement artifact

Each artifact reference carries a SHA-256 digest so a generated HIL permit is tied to the exact evidence record that was reviewed.

## Readiness command

Copy `tests/hil/single-servo-evidence.template.json` outside the repository or into a dedicated evidence folder, replace every placeholder with measured values, and record artifact hashes.

Then run:

```bash
python -m rci.hil.cli \
  --evidence path/to/single-servo-evidence.json \
  --permit-out path/to/single-servo-permit.json
```

A permit is generated only when the evidence schema is valid, all physical checks are true, and the joint/channel/protocol ID/driver/PWM frequency agree with canonical configuration.

The CLI never opens a serial port and never moves hardware.

## Physical HIL execution gate

PR-014 should remain open/draft until real bench evidence exists. After the measured evidence passes the readiness gate, the next patch in this same milestone may add the deliberately isolated physical single-servo driver/runner using the resulting permit.

That physical runner must still require:

1. the exact evidence digest from the permit,
2. an independent E-stop that is reachable and already tested,
3. start from the measured neutral point,
4. one servo only,
5. the narrow first-test angle envelope,
6. the measured maximum step size,
7. immediate power removal on unexpected motion/current/noise,
8. recorded telemetry/video/measurement evidence for every run.

Only after those physical records are reviewed may a joint's measured limits be promoted into production configuration. A single-servo pass does not make `servos.hardware_verified: true` for the full robot.
