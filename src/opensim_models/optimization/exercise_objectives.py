"""Facade module for exercise objectives to preserve backwards compatibility."""

from __future__ import annotations

from .objectives.core import ExerciseObjective, Phase
from .objectives.squat import SQUAT
from .objectives.deadlift import DEADLIFT
from .objectives.bench_press import BENCH_PRESS
from .objectives.snatch import SNATCH
from .objectives.clean_and_jerk import CLEAN_AND_JERK
from .objectives.gait import GAIT
from .objectives.sit_to_stand import SIT_TO_STAND

EXERCISE_OBJECTIVES: dict[str, ExerciseObjective] = {
    "squat": SQUAT,
    "deadlift": DEADLIFT,
    "bench_press": BENCH_PRESS,
    "snatch": SNATCH,
    "clean_and_jerk": CLEAN_AND_JERK,
    "gait": GAIT,
    "sit_to_stand": SIT_TO_STAND,
}

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

__all__ = [
    "Phase", 
    "ExerciseObjective", 
    "EXERCISE_OBJECTIVES", 
    "get_exercise_objective",
    "SQUAT", "DEADLIFT", "BENCH_PRESS", "SNATCH", "CLEAN_AND_JERK", "GAIT", "SIT_TO_STAND"
]
