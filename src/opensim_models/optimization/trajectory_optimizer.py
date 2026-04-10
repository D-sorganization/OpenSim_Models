"""Trajectory optimization utilities for exercise motion planning.

Provides helpers to interpolate phase-based objectives into dense keyframe
sequences and to configure OpenSim Moco trajectory optimization studies.

Design by Contract:
  - interpolate_phases requires num_points >= 2
  - create_moco_study validates that config references a known exercise
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from opensim_models.optimization.exercise_objectives import (
    ExerciseObjective,
    get_exercise_objective,
)
from opensim_models.shared.contracts.preconditions import (
    require_non_negative,
    require_positive,
)

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryConfig:
    """Configuration for a trajectory optimization run.

    Attributes:
        exercise_name: Canonical name of the exercise (must be registered).
        duration: Total movement duration in seconds.
        num_mesh_points: Number of mesh intervals for the Moco solver.
        max_iterations: Solver iteration limit.
        convergence_tolerance: Optimality convergence tolerance.
        constraint_tolerance: Constraint feasibility tolerance.
        weight_tracking: Weight for joint-angle tracking cost.
        weight_effort: Weight for control-effort minimisation cost.
    """

    exercise_name: str = "squat"
    duration: float = 3.0
    num_mesh_points: int = 50
    max_iterations: int = 1000
    convergence_tolerance: float = 1e-4
    constraint_tolerance: float = 1e-4
    weight_tracking: float = 10.0
    weight_effort: float = 1.0

    def __post_init__(self) -> None:
        require_positive(self.duration, "duration")
        require_positive(float(self.num_mesh_points), "num_mesh_points")
        require_positive(float(self.max_iterations), "max_iterations")
        require_positive(self.convergence_tolerance, "convergence_tolerance")
        require_positive(self.constraint_tolerance, "constraint_tolerance")
        require_non_negative(self.weight_tracking, "weight_tracking")
        require_non_negative(self.weight_effort, "weight_effort")


@dataclass
class TrajectoryResult:
    """Container for trajectory optimization output.

    Attributes:
        time: 1-D array of time values (seconds).
        coordinates: Mapping of coordinate name to 1-D array of angle values (rad).
        converged: Whether the solver reported convergence.
        objective_value: Final value of the composite objective function.
        iterations: Number of solver iterations used.
        config: The TrajectoryConfig that produced this result.
    """

    time: np.ndarray
    coordinates: dict[str, np.ndarray] = field(default_factory=dict)
    converged: bool = False
    objective_value: float = float("inf")
    iterations: int = 0
    config: TrajectoryConfig | None = None


def _collect_coords(objective: ExerciseObjective) -> set[str]:
    """Return all coordinate names referenced across all phases."""
    all_coords: set[str] = set()
    for phase in objective.phases:
        all_coords.update(phase.joint_targets.keys())
    return all_coords


def _interpolate_coord(
    coord: str,
    objective: ExerciseObjective,
    normalised: np.ndarray,
    num_points: int,
) -> np.ndarray:
    """Return a linearly interpolated trajectory array for one coordinate."""
    wp_times: list[float] = []
    wp_values: list[float] = []
    for phase in objective.phases:
        if coord in phase.joint_targets:
            wp_times.append(phase.time_fraction)
            wp_values.append(phase.joint_targets[coord])

    if len(wp_times) < 2:
        return np.full(num_points, wp_values[0] if wp_values else 0.0)
    return np.interp(normalised, wp_times, wp_values)


def interpolate_phases(
    objective: ExerciseObjective,
    num_points: int = 100,
    duration: float = 3.0,
) -> TrajectoryResult:
    """Generate a dense keyframe trajectory by linearly interpolating phases.

    Args:
        objective: The exercise objective whose phases define the waypoints.
        num_points: Number of output time-steps (must be >= 2).
        duration: Total duration in seconds.

    Returns:
        A TrajectoryResult with linearly interpolated coordinate trajectories.

    Raises:
        ValueError: If *num_points* < 2 or *duration* <= 0.
    """
    if num_points < 2:
        raise ValueError(f"num_points must be >= 2, got {num_points}")
    if duration <= 0:
        raise ValueError(f"duration must be > 0, got {duration}")

    time = np.linspace(0.0, duration, num_points)
    normalised = time / duration  # [0, 1]

    coordinates: dict[str, np.ndarray] = {
        coord: _interpolate_coord(coord, objective, normalised, num_points)
        for coord in sorted(_collect_coords(objective))
    }

    return TrajectoryResult(
        time=time,
        coordinates=coordinates,
        converged=True,
        objective_value=0.0,
        iterations=0,
    )


def _build_solver_dict(config: TrajectoryConfig) -> dict:
    """Return the MocoCasADiSolver sub-dict for a Moco study."""
    return {
        "type": "MocoCasADiSolver",
        "max_iterations": config.max_iterations,
        "convergence_tolerance": config.convergence_tolerance,
        "constraint_tolerance": config.constraint_tolerance,
        "num_mesh_intervals": config.num_mesh_points,
    }


def _build_problem_dict(
    config: TrajectoryConfig,
    objective: ExerciseObjective,
    guess: TrajectoryResult,
) -> dict:
    """Return the problem definition sub-dict for a Moco study."""
    return {
        "exercise": objective.name,
        "duration": config.duration,
        "coordinates": list(guess.coordinates.keys()),
        "cost_weights": {
            "tracking": config.weight_tracking,
            "effort": config.weight_effort,
        },
    }


def create_moco_study(config: TrajectoryConfig) -> dict:
    """Build a dict describing a Moco trajectory optimization problem.

    This does **not** require the OpenSim Python bindings; it returns a
    plain configuration dict that can be serialised or passed to an actual
    Moco solver when available.

    Args:
        config: Trajectory optimisation parameters.

    Returns:
        Dictionary with keys ``solver``, ``problem``, ``initial_guess``
        describing the full Moco study specification.

    Raises:
        KeyError: If *config.exercise_name* is not a registered exercise.
    """
    objective = get_exercise_objective(config.exercise_name)
    guess = interpolate_phases(
        objective, num_points=config.num_mesh_points, duration=config.duration
    )

    logger.info(
        "Created Moco study for '%s' (%d mesh points, %.1f s)",
        config.exercise_name,
        config.num_mesh_points,
        config.duration,
    )

    return {
        "solver": _build_solver_dict(config),
        "problem": _build_problem_dict(config, objective, guess),
        "initial_guess": {
            "time": guess.time.tolist(),
            "coordinates": {k: v.tolist() for k, v in guess.coordinates.items()},
        },
    }
