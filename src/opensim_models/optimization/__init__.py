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
from opensim_models.tools.forward_simulation import (
    ForwardSimulationResult,
    ForwardSimulationTool,
    add_coordinate_actuators,
    run_forward_simulation,
)

__all__ = [
    "EXERCISE_OBJECTIVES",
    "ExerciseObjective",
    "ForwardSimulationResult",
    "ForwardSimulationTool",
    "Phase",
    "TrajectoryConfig",
    "TrajectoryResult",
    "add_coordinate_actuators",
    "create_moco_study",
    "get_exercise_objective",
    "interpolate_phases",
    "run_forward_simulation",
]
