"""Small typed result container for expected recoverable outcomes."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Result[T]:
    value: T | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None
