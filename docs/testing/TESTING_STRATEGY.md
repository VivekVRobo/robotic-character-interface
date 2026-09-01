# Testing Strategy

The test pyramid includes unit, contract, integration, simulation, safety, fault injection, HIL, and E2E suites.

Safety/contract tests are merge-blocking. HIL is explicit and never runs by default. Real hardware evidence is kept separate from simulated pass results.

Critical required tests include out-of-range joint rejection, excessive velocity/acceleration rejection, expired/replayed command rejection, E-stop blocking motion, watchdog blocking motion, fault blocking arming, and invalid AI output being unable to move actuators.
