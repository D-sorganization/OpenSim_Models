"""Optimization objectives and trajectory planning for barbell exercises."""

from opensim_models.optimization._types import ExerciseObjective, Phase
from opensim_models.optimization.exercise_objectives import (
    EXERCISE_OBJECTIVES,
    get_exercise_objective,
)
from opensim_models.optimization.trajectory_optimizer import (
    TrajectoryConfig,
    TrajectoryResult,
    create_moco_study,
    interpolate_phases,
)

__all__ = [
    "EXERCISE_OBJECTIVES",
    "ExerciseObjective",
    "Phase",
    "TrajectoryConfig",
    "TrajectoryResult",
    "create_moco_study",
    "get_exercise_objective",
    "interpolate_phases",
]
