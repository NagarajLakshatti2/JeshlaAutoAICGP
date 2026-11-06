"""Shared delegation budget and cancellation controls for one coordinator run."""
from dataclasses import dataclass, field
from threading import Event
import time


@dataclass
class RunControl:
    remaining: dict
    max_depth: int = 2
    _cancelled: Event = field(default_factory=Event, repr=False)
    _started_at: float = field(default_factory=time.monotonic, init=False, repr=False)
    _initial_time_budget: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.remaining, dict) or not self.remaining:
            raise ValueError("A non-empty shared run budget is required.")
        if type(self.max_depth) is not int or not 1 <= self.max_depth <= 8:
            raise ValueError("Delegation depth must be between 1 and 8.")
        if any(not isinstance(key, str) or type(value) not in (int, float) or value < 0
               for key, value in self.remaining.items()):
            raise ValueError("Shared budget values must be non-negative numbers.")
        if "time_seconds" in self.remaining:
            self._initial_time_budget = self.remaining["time_seconds"]

    def cancel(self):
        self._cancelled.set()

    @property
    def cancelled(self):
        return self._cancelled.is_set()

    def check(self, depth: int):
        if self.cancelled:
            raise RuntimeError("Coordinator run was cancelled.")
        if type(depth) is not int or not 0 <= depth < self.max_depth:
            raise RuntimeError("Delegation depth limit reached.")
        if any(value < 0 for value in self.remaining.values()):
            raise RuntimeError("Shared coordinator budget was exceeded.")
        if self._initial_time_budget is not None:
            elapsed = time.monotonic() - self._started_at
            self.remaining["time_seconds"] = max(0.0, self._initial_time_budget - elapsed)
            if self.remaining["time_seconds"] <= 0:
                raise RuntimeError("Shared coordinator time budget is exhausted.")

    def charge(self, **costs):
        """Charge the shared budget before starting work; never permit overrun."""
        if any(key not in self.remaining or type(value) not in (int, float) or value < 0
               or value > self.remaining[key] for key, value in costs.items()):
            raise RuntimeError("Requested work exceeds the shared coordinator budget.")
        for key, value in costs.items():
            self.remaining[key] -= value

