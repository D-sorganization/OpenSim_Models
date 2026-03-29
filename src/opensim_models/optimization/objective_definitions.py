"""Exercise objective data definitions.

DRY: Phase and angle data for each exercise is split into per-category
modules and assembled into a single registry here. Downstream code imports
from ``exercise_objectives`` which re-exports the registry.
"""

from __future__ import annotations

from opensim_models.optimization._barbell_objectives import (
    BENCH_PRESS,
    DEADLIFT,
    SQUAT,
)
from opensim_models.optimization._movement_objectives import GAIT, SIT_TO_STAND
from opensim_models.optimization._olympic_objectives import CLEAN_AND_JERK, SNATCH
from opensim_models.optimization._types import ExerciseObjective

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

EXERCISE_OBJECTIVES: dict[str, ExerciseObjective] = {
    "squat": SQUAT,
    "deadlift": DEADLIFT,
    "bench_press": BENCH_PRESS,
    "snatch": SNATCH,
    "clean_and_jerk": CLEAN_AND_JERK,
    "gait": GAIT,
    "sit_to_stand": SIT_TO_STAND,
}
