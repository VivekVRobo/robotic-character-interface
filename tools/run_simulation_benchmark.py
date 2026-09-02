from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from rci.behavior import BehaviorIntent
from rci.characters.contracts import MotionCue, MotionStyle
from rci.robotics import RobotModel, load_reference_profile
from rci.simulation.runtime import SimulationRuntime

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "configs" / "simulation" / "reference_arm.yaml"
CUES = (
    MotionCue.LISTEN,
    MotionCue.ACKNOWLEDGE,
    MotionCue.PRESENT,
    MotionCue.CAUTION,
    MotionCue.CELEBRATE,
    MotionCue.THINK,
)
STYLES = (MotionStyle.RESTRAINED, MotionStyle.STANDARD, MotionStyle.EXPRESSIVE)


async def run_benchmark(repetitions: int) -> dict[str, object]:
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    model = RobotModel(load_reference_profile(PROFILE))
    runtime = SimulationRuntime(model)
    cycles = 0
    estop_recoveries = 0
    total_steps = 0
    total_simulated_duration_s = 0.0
    max_simulated_duration_s = 0.0
    max_current_ma = 0

    try:
        for repetition in range(repetitions):
            for cue in CUES:
                for style in STYLES:
                    cycles += 1
                    intent = BehaviorIntent(
                        interaction_id=f"benchmark-{repetition}-{cycles}",
                        decision_id=f"decision-{repetition}-{cycles}",
                        source_character="aurelia",
                        expression="neutral",
                        cue=cue,
                        style=style,
                    )
                    report = await runtime.execute_behavior(intent)
                    total_steps += report.simulation_steps
                    total_simulated_duration_s += report.simulated_duration_s
                    max_simulated_duration_s = max(
                        max_simulated_duration_s,
                        report.simulated_duration_s,
                    )
                    max_current_ma = max(
                        max_current_ma,
                        *(joint.current_ma for joint in report.telemetry.joints),
                    )

                    if cycles % 12 == 0:
                        await runtime.estop()
                        if not runtime.reset_estop():
                            raise RuntimeError("simulation E-stop failed to reset during soak benchmark")
                        estop_recoveries += 1

        diagnostics = await runtime.diagnostics()
        telemetry = runtime.telemetry()
        result: dict[str, object] = {
            "schema_version": "rci.simulation_benchmark.v1",
            "profile_id": model.profile.profile_id,
            "simulation_only": True,
            "hardware_verified": False,
            "provenance": model.profile.provenance.source,
            "cycles": cycles,
            "estop_recoveries": estop_recoveries,
            "total_steps": total_steps,
            "total_simulated_duration_s": round(total_simulated_duration_s, 6),
            "max_simulated_duration_s": round(max_simulated_duration_s, 6),
            "max_current_ma": max_current_ma,
            "gateway": {
                "sent": diagnostics.sent_count,
                "acknowledged": diagnostics.acknowledged_count,
                "rejected": diagnostics.rejected_count,
            },
            "final_telemetry": {
                "state": telemetry.state.name,
                "supply_mv": telemetry.supply_mv,
                "joints": [
                    {
                        "joint_id": joint.joint_id,
                        "position_cdeg": joint.position_cdeg,
                        "velocity_cdeg_s": joint.velocity_cdeg_s,
                        "current_ma": joint.current_ma,
                    }
                    for joint in telemetry.joints
                ],
            },
        }
        canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
        result["sha256"] = hashlib.sha256(canonical).hexdigest()
        return result
    finally:
        await runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic RCI digital-twin soak benchmark")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = asyncio.run(run_benchmark(args.repetitions))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
