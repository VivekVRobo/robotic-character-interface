"""Application entry point."""

from __future__ import annotations

import asyncio


async def run() -> None:
    """Start the RCI runtime.

    PR-001 intentionally provides only the executable package foundation. The
    dependency graph is introduced in later ordered milestones.
    """
    return None


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
