"""Core classes for OpenSim Moco trajectory planning objectives.

Design by Contract: all angle values are stored in radians internally.
Phases must have strictly monotonic time fractions in [0, 1].
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Phase:
    """A single phase within an exercise movement pattern.

    Attributes:
        name: Human-readable phase label (e.g. "bottom", "lockout").
        time_fraction: Normalised time within [0, 1] at which this phase occurs.
        joint_targets: Mapping of coordinate name to target angle in radians.
        description: Optional narrative description of the phase.
    """

    name: str
    time_fraction: float
    joint_targets: dict[str, float] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.time_fraction <= 1.0:
            raise ValueError(
                f"Phase '{self.name}' time_fraction must be in [0, 1], "
                f"got {self.time_fraction}"
            )


@dataclass(frozen=True)
class ExerciseObjective:
    """Complete movement objective for an exercise.

    Attributes:
        name: Canonical exercise name (e.g. "squat").
        phases: Ordered sequence of movement phases.
        primary_coordinates: Coordinate names most relevant to the exercise.
        description: Narrative summary of the movement.
    """

    name: str
    phases: tuple[Phase, ...]
    primary_coordinates: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if len(self.phases) < 2:
            raise ValueError(
                f"Exercise '{self.name}' must have at least 2 phases, "
                f"got {len(self.phases)}"
            )
        fractions = [p.time_fraction for p in self.phases]
        for i in range(1, len(fractions)):
            if fractions[i] <= fractions[i - 1]:
                raise ValueError(
                    f"Exercise '{self.name}' phases must have strictly monotonic "
                    f"time fractions. Phase '{self.phases[i].name}' "
                    f"({fractions[i]}) <= '{self.phases[i - 1].name}' "
                    f"({fractions[i - 1]})"
                )
