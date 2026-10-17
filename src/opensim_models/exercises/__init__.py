"""Exercise-specific OpenSim model builders."""

from __future__ import annotations

from collections.abc import Callable

from .base import ExerciseModelBuilder
from .bench_press.bench_press_model import (
    BenchPressModelBuilder,
    build_bench_press_model,
)
from .clean_and_jerk.clean_and_jerk_model import (
    CleanAndJerkModelBuilder,
    build_clean_and_jerk_model,
)
from .deadlift.deadlift_model import DeadliftModelBuilder, build_deadlift_model
from .gait.gait_model import GaitModelBuilder, build_gait_model
from .sit_to_stand.sit_to_stand_model import (
    SitToStandModelBuilder,
    build_sit_to_stand_model,
)
from .snatch.snatch_model import SnatchModelBuilder, build_snatch_model
from .squat.squat_model import SquatModelBuilder, build_squat_model

# Single authoritative registry of all supported exercises.
# Keys are the CLI exercise names; values are convenience build functions.
EXERCISE_BUILDERS: dict[str, Callable[..., str]] = {
    "bench_press": build_bench_press_model,
    "clean_and_jerk": build_clean_and_jerk_model,
    "deadlift": build_deadlift_model,
    "gait": build_gait_model,
    "sit_to_stand": build_sit_to_stand_model,
    "snatch": build_snatch_model,
    "squat": build_squat_model,
}

# Builder class behind each registry entry (MuJoCo_Models ``EXERCISE_REGISTRY``).
EXERCISE_REGISTRY: dict[str, type[ExerciseModelBuilder]] = {
    "bench_press": BenchPressModelBuilder,
    "clean_and_jerk": CleanAndJerkModelBuilder,
    "deadlift": DeadliftModelBuilder,
    "gait": GaitModelBuilder,
    "sit_to_stand": SitToStandModelBuilder,
    "snatch": SnatchModelBuilder,
    "squat": SquatModelBuilder,
}

# Exercises whose feet start seated at the contact equilibrium (#472).
SEATED_EXERCISES: tuple[str, ...] = tuple(
    name for name, cls in EXERCISE_REGISTRY.items() if cls.seat_feet_at_equilibrium
)

__all__ = [
    "EXERCISE_BUILDERS",
    "EXERCISE_REGISTRY",
    "SEATED_EXERCISES",
    "build_bench_press_model",
    "build_clean_and_jerk_model",
    "build_deadlift_model",
    "build_gait_model",
    "build_sit_to_stand_model",
    "build_snatch_model",
    "build_squat_model",
]
