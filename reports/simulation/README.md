# Simulation Evidence

This directory is reserved for software-generated digital-twin evidence.

The authoritative CI benchmark is produced on every Backend CI run by `tools/run_simulation_benchmark.py` and uploaded as the `rci-simulation-benchmark` workflow artifact.

The benchmark is deliberately deterministic and contains no wall-clock performance claim and no physical measurement claim. It records simulated behavior cycles, convergence steps, simulated duration, simulated current, E-stop recovery count, gateway ACK/rejection counts, final telemetry, provenance, and a SHA-256 digest.

Physical photographs, voltage/current measurements, servo calibration data, mechanical measurements, and HIL results must never be placed here as simulated substitutes. Real hardware evidence belongs under the hardware/HIL evidence workflow only after it has actually been measured.
