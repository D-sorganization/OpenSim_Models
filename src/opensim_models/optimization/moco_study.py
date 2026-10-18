"""Real OpenSim Moco trajectory optimization of the exercise keyframes (#470).

:func:`create_moco_study` builds an ``opensim.MocoStudy`` for a registered
exercise on the Moco-ready model of :mod:`._moco_model` (CoordinateActuators
on every coordinate, optionally reduced): coordinate value bounds from the
coordinate ranges, a ``MocoStateTrackingGoal`` on the phase keyframes
interpolated by :func:`interpolate_phases`, a ``MocoControlGoal`` for effort
and a ``MocoCasADiSolver`` configured from the :class:`TrajectoryConfig`,
seeded with the keyframe trajectory (untracked coordinates at their default
pose) as its initial guess.

:func:`solve_trajectory` solves that study and reports the solution as a
:class:`TrajectoryResult`; :func:`phase_keyframe_errors` measures how close a
trajectory comes to each phase keyframe.

Design by Contract:
    - Preconditions: see :mod:`._moco_model`; an unknown exercise raises
      KeyError and missing OpenSim raises RuntimeError, never a stand-in.
    - Postconditions: the returned study is a real ``opensim.MocoStudy``;
      a solved result's ``converged``, ``objective_value`` and ``iterations``
      are the solver's own.
"""

from __future__ import annotations

import logging
from collections.abc import Collection
from typing import Any

import numpy as np

from opensim_models.optimization._moco_model import (
    ACTUATOR_OPTIMAL_FORCE,
    FIXED_PELVIS_STILL_ARMS,
    FULL_MODEL,
    WELD_KEYFRAME_TOL_RAD,
    ModelReduction,
    build_moco_model,
    coordinate_names,
    moco_ready_osim,
    require_opensim,
)
from opensim_models.optimization._types import ExerciseObjective
from opensim_models.optimization.exercise_objectives import get_exercise_objective
from opensim_models.optimization.trajectory_optimizer import (
    TrajectoryConfig,
    TrajectoryResult,
    interpolate_phases,
)

try:
    import opensim
except ImportError:
    opensim = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

__all__ = [
    "ACTUATOR_OPTIMAL_FORCE",
    "FIXED_PELVIS_STILL_ARMS",
    "FULL_MODEL",
    "GUESS_POINTS_PER_INTERVAL",
    "WELD_KEYFRAME_TOL_RAD",
    "ModelReduction",
    "build_moco_model",
    "create_moco_study",
    "moco_ready_osim",
    "phase_keyframe_errors",
    "solve_trajectory",
]

# Keyframe-guess samples per mesh interval (Hermite-Simpson has a midpoint).
GUESS_POINTS_PER_INTERVAL = 2
_VALUE_SUFFIX = "/value"


def _value_path(model: Any, name: str) -> str:
    """Moco state path of a coordinate value, e.g. ``/jointset/knee_r/...``."""
    path = model.getCoordinateSet().get(name).getAbsolutePathString()
    return f"{path}{_VALUE_SUFFIX}"


def _states_table(model: Any, time: np.ndarray, values: dict[str, np.ndarray]) -> Any:
    """TimeSeriesTable of coordinate values (radians) keyed by state path."""
    table = opensim.TimeSeriesTable()
    table.setColumnLabels([_value_path(model, name) for name in values])
    table.addTableMetaDataString("inDegrees", "no")
    columns = list(values.values())
    for k, t in enumerate(time):
        table.appendRow(float(t), opensim.RowVector([float(c[k]) for c in columns]))
    return table


def _keyframes(
    model: Any, config: TrajectoryConfig, objective: ExerciseObjective
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Keyframe trajectory of the model's coordinates (welded ones dropped)."""
    dense = interpolate_phases(
        objective,
        num_points=GUESS_POINTS_PER_INTERVAL * config.num_mesh_points + 1,
        duration=config.duration,
    )
    present = set(coordinate_names(model))
    tracked = {k: v for k, v in dense.coordinates.items() if k in present}
    return dense.time, tracked


def _defaults_filled(
    model: Any, time: np.ndarray, tracked: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    """Keyframe values, plus untracked coordinates held at their defaults."""
    coords = model.getCoordinateSet()
    filled = dict(tracked)
    for name in coordinate_names(model):
        if name not in filled:
            filled[name] = np.full(time.shape, coords.get(name).getDefaultValue())
    return filled


def _configure_problem(
    problem: Any, model: Any, config: TrajectoryConfig, reference: Any
) -> None:
    problem.setModelAsCopy(model)
    problem.setTimeBounds(0.0, config.duration)
    coords = model.getCoordinateSet()
    for name in coordinate_names(model):
        coord = coords.get(name)
        bounds = [coord.getRangeMin(), coord.getRangeMax()]
        problem.setStateInfo(_value_path(model, name), bounds)
    tracking = opensim.MocoStateTrackingGoal(
        "keyframe_tracking", config.weight_tracking
    )
    tracking.setReference(opensim.TableProcessor(reference))
    problem.addGoal(tracking)
    problem.addGoal(opensim.MocoControlGoal("effort", config.weight_effort))


def _configure_solver(study: Any, config: TrajectoryConfig, guess_table: Any) -> None:
    solver = study.initCasADiSolver()
    solver.set_num_mesh_intervals(config.num_mesh_points)
    solver.set_optim_max_iterations(config.max_iterations)
    solver.set_optim_convergence_tolerance(config.convergence_tolerance)
    solver.set_optim_constraint_tolerance(config.constraint_tolerance)
    solver.set_verbosity(0)
    guess = solver.createGuess()
    guess.setStatesTrajectory(guess_table, True, True)
    solver.setGuess(guess)


def create_moco_study(
    config: TrajectoryConfig, reduction: ModelReduction = FULL_MODEL
) -> Any:
    """Build a real ``opensim.MocoStudy`` tracking the exercise keyframes.

    Args:
        config: Trajectory optimisation parameters (duration, mesh,
            tolerances, iteration limit and goal weights).
        reduction: Optional model reduction (welded joints, contact).

    Returns:
        An ``opensim.MocoStudy`` with its CasADi solver set up, ready to solve.

    Raises:
        RuntimeError: OpenSim with Moco is not installed.
        KeyError: *config.exercise_name* is not a registered exercise.
        ValueError: The reduction welds a joint the keyframes move.
    """
    require_opensim()
    objective = get_exercise_objective(config.exercise_name)
    model = build_moco_model(objective, reduction)
    time, tracked = _keyframes(model, config, objective)
    study = opensim.MocoStudy()
    study.setName(f"{config.exercise_name}_keyframe_tracking")
    reference = _states_table(model, time, tracked)
    _configure_problem(study.updProblem(), model, config, reference)
    guess = _states_table(model, time, _defaults_filled(model, time, tracked))
    _configure_solver(study, config, guess)
    logger.info(
        "Built MocoStudy for '%s' (%d coordinates, %d mesh intervals, %.2f s)",
        config.exercise_name,
        len(coordinate_names(model)),
        config.num_mesh_points,
        config.duration,
    )
    return study


def _solution_coordinates(solution: Any) -> dict[str, np.ndarray]:
    """Coordinate name -> solved values, from the solution's state paths."""
    return {
        path[: -len(_VALUE_SUFFIX)].rsplit("/", 1)[-1]: np.asarray(
            solution.getStateMat(path)
        ).ravel()
        for path in solution.getStateNames()
        if path.endswith(_VALUE_SUFFIX)
    }


def solve_trajectory(
    config: TrajectoryConfig, reduction: ModelReduction = FULL_MODEL
) -> TrajectoryResult:
    """Solve the keyframe-tracking study and return its trajectory.

    Returns:
        A TrajectoryResult whose ``converged`` is Moco's success flag and
        whose ``objective_value`` and ``iterations`` are the solver's own.
    """
    solution = create_moco_study(config, reduction).solve()
    converged = bool(solution.success())
    if not converged:
        logger.warning("Moco did not converge: %s", solution.getStatus())
        solution.unseal()
    return TrajectoryResult(
        time=np.asarray(solution.getTimeMat()).ravel(),
        coordinates=_solution_coordinates(solution),
        converged=converged,
        objective_value=float(solution.getObjective()),
        iterations=int(solution.getNumIterations()),
        config=config,
    )


def phase_keyframe_errors(
    result: TrajectoryResult,
    objective: ExerciseObjective,
    coordinates: Collection[str] | None = None,
) -> dict[str, float]:
    """Largest absolute coordinate error (rad) at each phase keyframe.

    Args:
        result: A trajectory, e.g. from :func:`solve_trajectory`.
        objective: The exercise whose phase keyframes are measured.
        coordinates: Coordinates to measure; every keyframe coordinate when
            None.  A reduced study's welded coordinates are excluded this way
            (they sit within ``WELD_KEYFRAME_TOL_RAD`` of every keyframe).

    Raises:
        ValueError: The result has no time axis or lacks a measured coordinate.
    """
    if result.time.size < 2:
        raise ValueError("result has no time axis to evaluate keyframes on")
    duration = float(result.time[-1] - result.time[0])
    errors: dict[str, float] = {}
    for phase in objective.phases:
        names = [
            n for n in phase.joint_targets if coordinates is None or n in coordinates
        ]
        missing = sorted(set(names) - set(result.coordinates))
        if not names or missing:
            raise ValueError(f"{phase.name}: result lacks coordinates {missing}")
        t = float(result.time[0]) + phase.time_fraction * duration
        errors[phase.name] = max(
            abs(
                float(np.interp(t, result.time, result.coordinates[n]))
                - phase.joint_targets[n]
            )
            for n in names
        )
    return errors
