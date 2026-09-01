# Hardware-in-the-loop tests

Physical HIL never runs in default GitHub-hosted CI.

PR-014 introduces a software readiness gate for exactly one servo. A real HIL run is allowed only after an operator records measured electrical, mechanical, angle/pulse, E-stop, and wiring evidence and the `SingleServoHilGate` mints a content-bound permit.

Default CI may validate the evidence schema, fail-closed permit logic, and compiled firmware HIL guard. Those checks are **not physical validation** and must never be reported as a successful servo movement.

The first physical record should be created from `single-servo-evidence.template.json`, accompanied by content-addressed wiring and measurement artifacts. The production `configs/servos.yaml` remains globally unverified until broader multi-joint validation is completed.
