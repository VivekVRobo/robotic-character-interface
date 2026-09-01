"""CLI for validating measured single-servo HIL evidence; never actuates hardware."""

from __future__ import annotations

import argparse
from pathlib import Path

from rci.config.loader import ConfigLoader
from rci.hil.gate import SingleServoHilGate
from rci.hil.io import HilEvidenceError, load_evidence, write_permit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--permit-out", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = ConfigLoader(args.config_dir).load()
        evidence = load_evidence(args.evidence)
    except (HilEvidenceError, ValueError) as exc:
        print(f"HIL evidence rejected: {exc}")
        return 2

    decision = SingleServoHilGate(settings).evaluate(evidence)
    if not decision.approved or decision.permit is None:
        reasons = ", ".join(reason.value for reason in decision.reasons)
        print(f"HIL activation denied: {reasons}")
        return 3

    if args.permit_out is not None:
        try:
            write_permit(args.permit_out, decision.permit)
        except HilEvidenceError as exc:
            print(f"HIL permit write failed: {exc}")
            return 4
        print(f"HIL readiness permit written: {args.permit_out}")
    else:
        print(decision.permit.model_dump_json(indent=2))

    print("Readiness only: this command does not energize or move a servo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
