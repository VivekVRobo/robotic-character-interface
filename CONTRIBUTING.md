# Contributing

Development follows small reviewable PRs and the ordered milestones in `docs/DEVELOPMENT_ROADMAP.md`.

## Required checks

- Ruff lint + format
- mypy
- pytest
- contract tests for protocol/schema changes
- safety tests for motion/safety changes

## Safety-sensitive changes

Any change touching actuator command paths, joint/workspace limits, command freshness, watchdogs, E-stop handling, or firmware validation must include negative/boundary tests and must not introduce an alternate actuator path.
