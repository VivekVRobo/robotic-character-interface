from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from rci.behavior import BehaviorIntent
from rci.behavior.embodiment import SimulationBehaviorEmbodimentPlanner
from rci.characters.contracts import MotionCue, MotionStyle
from rci.domain.enums import MotionDecision, SystemState
from rci.robotics import RobotController, RobotModel, load_reference_profile
from rci.safety.models import CartesianPoint, MotionCandidate, MotionDynamics, SafetyViolationCode
from rci.simulation.digital_twin import DigitalTwinRobot
from rci.simulation.safety import build_simulation_supervisor

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "configs" / "simulation" / "reference_arm.yaml"


def _baseline(model: RobotModel) -> tuple[MotionCandidate, MotionDynamics]:
    twin = DigitalTwinRobot(model)
    controller = RobotController(model)
    embodiment = SimulationBehaviorEmbodimentPlanner(model)
    intent = BehaviorIntent(
        interaction_id="safety-evidence-interaction",
        decision_id="safety-evidence-decision",
        source_character="aurelia",
        expression="neutral",
        cue=MotionCue.PRESENT,
        style=MotionStyle.STANDARD,
    )
    goal = embodiment.plan(intent)
    planned = controller.plan_joint_targets(
        current_joints_deg=twin.state.positions_deg,
        target_joints_deg=goal.target_joints_deg,
        sample_period_s=0.02,
    )
    return planned.terminal_safety_inputs(
        system_state=SystemState.ARMED,
        estop_active=False,
        command_age_ms=0.0,
        heartbeat_age_ms=10.0,
    )


def _evaluate_case(
    model: RobotModel,
    name: str,
    candidate: MotionCandidate,
    dynamics: MotionDynamics,
    expected_decision: MotionDecision,
    expected_code: SafetyViolationCode | None,
) -> dict[str, object]:
    supervisor = build_simulation_supervisor(model)
    result = supervisor.evaluate(candidate, dynamics)
    codes = [violation.code.value for violation in result.violations]
    passed = result.decision is expected_decision
    if expected_code is None:
        passed = passed and not codes and result.authorization is not None
    else:
        passed = passed and expected_code.value in codes and result.authorization is None
    return {
        "name": name,
        "expected_decision": expected_decision.value,
        "actual_decision": result.decision.value,
        "expected_violation": expected_code.value if expected_code is not None else None,
        "actual_violations": codes,
        "authorization_minted": result.authorization is not None,
        "passed": passed,
    }


def run_campaign() -> dict[str, object]:
    model = RobotModel(load_reference_profile(PROFILE))
    baseline_candidate, baseline_dynamics = _baseline(model)
    policy = build_simulation_supervisor(model).envelope.motion_policy
    if policy is None:
        raise RuntimeError("simulation safety profile must provide a motion policy")

    joint_name = sorted(model.profile.joints)[0]
    joint = model.profile.joints[joint_name]

    joint_targets = dict(baseline_candidate.joint_targets_deg)
    joint_targets[joint_name] = joint.upper_deg + 1.0

    high_velocity = dict(baseline_dynamics.joint_velocities_deg_s)
    high_velocity[joint_name] = policy.max_velocity_deg_s + 1.0

    high_acceleration = dict(baseline_dynamics.joint_accelerations_deg_s2)
    high_acceleration[joint_name] = policy.max_acceleration_deg_s2 + 1.0

    cases = [
        _evaluate_case(
            model,
            "baseline_authorization",
            baseline_candidate,
            baseline_dynamics,
            MotionDecision.APPROVE,
            None,
        ),
        _evaluate_case(
            model,
            "state_not_allowed",
            replace(baseline_candidate, system_state=SystemState.IDLE),
            baseline_dynamics,
            MotionDecision.REJECT,
            SafetyViolationCode.STATE_NOT_ALLOWED,
        ),
        _evaluate_case(
            model,
            "physical_estop_active",
            replace(baseline_candidate, estop_active=True),
            baseline_dynamics,
            MotionDecision.ESTOP,
            SafetyViolationCode.LIFECYCLE_ESTOP_LATCHED,
        ),
        _evaluate_case(
            model,
            "joint_limit_violation",
            replace(baseline_candidate, joint_targets_deg=joint_targets),
            baseline_dynamics,
            MotionDecision.REJECT,
            SafetyViolationCode.JOINT_LIMIT_VIOLATION,
        ),
        _evaluate_case(
            model,
            "workspace_limit_violation",
            replace(
                baseline_candidate,
                workspace_point_mm=CartesianPoint(1_000_000.0, 1_000_000.0, 1_000_000.0),
            ),
            baseline_dynamics,
            MotionDecision.REJECT,
            SafetyViolationCode.WORKSPACE_LIMIT_VIOLATION,
        ),
        _evaluate_case(
            model,
            "stale_command",
            baseline_candidate,
            replace(baseline_dynamics, command_age_ms=policy.command_ttl_ms + 1.0),
            MotionDecision.REJECT,
            SafetyViolationCode.COMMAND_STALE,
        ),
        _evaluate_case(
            model,
            "stale_heartbeat_latches_estop",
            baseline_candidate,
            replace(
                baseline_dynamics,
                heartbeat_age_ms=policy.heartbeat_timeout_ms + 1.0,
            ),
            MotionDecision.ESTOP,
            SafetyViolationCode.LIFECYCLE_ESTOP_LATCHED,
        ),
        _evaluate_case(
            model,
            "velocity_limit_violation",
            baseline_candidate,
            replace(baseline_dynamics, joint_velocities_deg_s=high_velocity),
            MotionDecision.REJECT,
            SafetyViolationCode.VELOCITY_LIMIT_VIOLATION,
        ),
        _evaluate_case(
            model,
            "acceleration_limit_violation",
            baseline_candidate,
            replace(baseline_dynamics, joint_accelerations_deg_s2=high_acceleration),
            MotionDecision.REJECT,
            SafetyViolationCode.ACCELERATION_LIMIT_VIOLATION,
        ),
    ]

    result: dict[str, object] = {
        "schema_version": "rci.motion_safety_evidence.v1",
        "profile_id": model.profile.profile_id,
        "evidence_type": "deterministic_software_safety_campaign",
        "simulation_only": True,
        "hardware_verified": False,
        "physical_motion": False,
        "provenance": model.profile.provenance.source,
        "case_count": len(cases),
        "passed_count": sum(bool(case["passed"]) for case in cases),
        "all_passed": all(bool(case["passed"]) for case in cases),
        "cases": cases,
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["sha256"] = hashlib.sha256(canonical).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run deterministic RCI motion-safety challenge cases"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = run_campaign()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)

    if not result["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
