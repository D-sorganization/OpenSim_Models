"""Exercise-specific OpenSim model builders."""

from __future__ import annotations

from collections.abc import Callable

from .bench_press.bench_press_model import (
    build_bench_press_model,
)
from .clean_and_jerk.clean_and_jerk_model import (
    build_clean_and_jerk_model,
)
from .deadlift.deadlift_model import build_deadlift_model
from .gait.gait_model import build_gait_model
from .sit_to_stand.sit_to_stand_model import (
    build_sit_to_stand_model,
)
from .snatch.snatch_model import build_snatch_model
from .squat.squat_model import build_squat_model

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

__all__ = [
    "EXERCISE_BUILDERS",
    "build_bench_press_model",
    "build_clean_and_jerk_model",
    "build_deadlift_model",
    "build_gait_model",
    "build_sit_to_stand_model",
    "build_snatch_model",
    "build_squat_model",
]
