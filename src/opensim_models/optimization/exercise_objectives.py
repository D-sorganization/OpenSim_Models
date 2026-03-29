"""Exercise-specific optimization objectives for OpenSim Moco trajectory planning.

This module re-exports the Phase/ExerciseObjective types from ``_types`` and
the objective registry from ``objective_definitions`` so that existing import
paths remain stable.

Design by Contract: all angle values are stored in radians internally.
Phases must have strictly monotonic time fractions in [0, 1].
"""

from __future__ import annotations

import logging

from opensim_models.optimization._types import ExerciseObjective, Phase
from opensim_models.optimization.objective_definitions import EXERCISE_OBJECTIVES

logger = logging.getLogger(__name__)

__all__ = [
    "EXERCISE_OBJECTIVES",
    "ExerciseObjective",
    "Phase",
    "get_exercise_objective",
]


def get_exercise_objective(name: str) -> ExerciseObjective:
    """Look up an exercise objective by canonical name.

    Raises:
        KeyError: If *name* is not a registered exercise.
    """
    try:
        return EXERCISE_OBJECTIVES[name]
    except KeyError:
        available = ", ".join(sorted(EXERCISE_OBJECTIVES))
        raise KeyError(f"Unknown exercise '{name}'. Available: {available}") from None
