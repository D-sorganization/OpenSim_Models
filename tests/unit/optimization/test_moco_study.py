"""Real OpenSim Moco study for every exercise, and a headless squat solve (#470).

The squat solve is the acceptance test: a reduced problem
(``FIXED_PELVIS_STILL_ARMS``, few mesh intervals, a loose but stated
convergence tolerance) that must converge within a time budget and pass
through every phase keyframe, bottom and lockout included, within
``KEYFRAME_TOL_RAD``.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.optimization import _moco_model
from opensim_models.optimization.exercise_objectives import (
    EXERCISE_OBJECTIVES,
    get_exercise_objective,
)
from opensim_models.optimization.moco_study import (
    FIXED_PELVIS_STILL_ARMS,
    WELD_KEYFRAME_TOL_RAD,
    ModelReduction,
    create_moco_study,
    moco_ready_osim,
    phase_keyframe_errors,
    solve_trajectory,
)
from opensim_models.optimization.trajectory_optimizer import (
    TrajectoryConfig,
    interpolate_phases,
)

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None or not hasattr(opensim, "MocoStudy"),
    reason="opensim with Moco is not installed in this Python environment",
)

# Reduced squat: the acceptance numbers below are stated, never loosened.
SQUAT_MESH_INTERVALS = 20  # 0.15 s apart over the 3 s lift
SQUAT_TOLERANCE = 1e-3  # IPOPT convergence and constraint tolerance
SQUAT_MAX_ITERATIONS = 500
SQUAT_TIME_BUDGET_S = 240.0  # well under 5 minutes on a laptop
KEYFRAME_TOL_RAD = math.radians(3.0)


# ---------------------------------------------------------------------------
# Pure-Python contracts (no OpenSim needed)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_moco_study_raises_without_opensim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing OpenSim is an error, never a stand-in study."""
    monkeypatch.setattr(_moco_model, "opensim", None)
    with pytest.raises(RuntimeError, match="OpenSim is not installed"):
        create_moco_study(TrajectoryConfig(exercise_name="squat"))


@pytest.mark.unit
def test_moco_ready_osim_has_no_free_joint() -> None:
    xml = moco_ready_osim("squat")
    assert "<FreeJoint" not in xml
    assert 'CustomJoint name="ground_pelvis"' in xml


@pytest.mark.unit
def test_moco_ready_osim_can_drop_ground_contact() -> None:
    assert "SmoothSphereHalfSpaceForce" in moco_ready_osim("squat")
    assert "SmoothSphereHalfSpaceForce" not in moco_ready_osim(
        "squat", ground_contact=False
    )


@pytest.mark.unit
def test_moco_ready_osim_rejects_unknown_exercise() -> None:
    with pytest.raises(KeyError, match="curls_in_squat_rack"):
        moco_ready_osim("curls_in_squat_rack")


@pytest.mark.unit
def test_keyframe_errors_are_zero_on_the_keyframe_interpolation() -> None:
    objective = get_exercise_objective("squat")
    exact = interpolate_phases(objective, num_points=201, duration=3.0)
    errors = phase_keyframe_errors(exact, objective)
    assert set(errors) == {p.name for p in objective.phases}
    assert max(errors.values()) < 1e-12


@pytest.mark.unit
def test_keyframe_errors_measure_the_largest_offset() -> None:
    objective = get_exercise_objective("squat")
    shifted = interpolate_phases(objective, num_points=201, duration=3.0)
    shifted.coordinates["knee_r_flex"] = shifted.coordinates["knee_r_flex"] + 0.1
    errors = phase_keyframe_errors(shifted, objective)
    assert all(e == pytest.approx(0.1) for e in errors.values())


@pytest.mark.unit
def test_keyframe_errors_reject_results_missing_coordinates() -> None:
    objective = get_exercise_objective("squat")
    partial = interpolate_phases(objective, num_points=11, duration=3.0)
    del partial.coordinates["knee_r_flex"]
    with pytest.raises(ValueError, match="knee_r_flex"):
        phase_keyframe_errors(partial, objective)


@pytest.mark.unit
def test_keyframe_errors_can_measure_a_subset() -> None:
    objective = get_exercise_objective("squat")
    partial = interpolate_phases(objective, num_points=201, duration=3.0)
    del partial.coordinates["shoulder_r_flex"]
    kept = set(partial.coordinates)
    assert max(phase_keyframe_errors(partial, objective, kept).values()) < 1e-12


@pytest.mark.unit
def test_every_objective_has_a_model_builder() -> None:
    assert set(EXERCISE_OBJECTIVES) <= set(EXERCISE_BUILDERS)


# ---------------------------------------------------------------------------
# Real OpenSim Moco
# ---------------------------------------------------------------------------


@pytest.mark.requires_opensim
@needs_opensim
def test_unknown_exercise_raises_key_error() -> None:
    with pytest.raises(KeyError, match="definitely_not_an_exercise"):
        create_moco_study(TrajectoryConfig(exercise_name="definitely_not_an_exercise"))


@pytest.mark.requires_opensim
@needs_opensim
@pytest.mark.parametrize("exercise", sorted(EXERCISE_OBJECTIVES))
def test_study_builds_and_validates(
    exercise: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each lift's study is a real MocoStudy whose problem the solver accepts."""
    monkeypatch.chdir(tmp_path)
    study = create_moco_study(
        TrajectoryConfig(exercise_name=exercise, num_mesh_points=5)
    )
    assert isinstance(study, opensim.MocoStudy)

    problem = study.getProblem()
    rep = problem.createRep()  # validates goals, bounds and references
    names = set(rep.createStateInfoNames())
    model = rep.getModelBase()
    assert model.getNumControls() == model.getCoordinateSet().getSize()
    for coord_name in get_exercise_objective(exercise).phases[0].joint_targets:
        path = model.getCoordinateSet().get(coord_name).getAbsolutePathString()
        assert f"{path}/value" in names
        info = rep.getStateInfo(f"{path}/value")
        coord = model.getCoordinateSet().get(coord_name)
        assert info.getBounds().getLower() == pytest.approx(coord.getRangeMin())
        assert info.getBounds().getUpper() == pytest.approx(coord.getRangeMax())

    solver = opensim.MocoCasADiSolver.safeDownCast(study.updSolver())
    assert solver.get_num_mesh_intervals() == 5
    guess = solver.getGuess()  # built and validated against the problem
    assert guess.isCompatible(rep, False, True)


@pytest.mark.requires_opensim
@needs_opensim
def test_reduction_welds_still_joints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fixed-pelvis squat keeps only the lumbar and leg coordinates."""
    monkeypatch.chdir(tmp_path)
    study = create_moco_study(
        TrajectoryConfig(exercise_name="squat", num_mesh_points=5),
        FIXED_PELVIS_STILL_ARMS,
    )
    rep = study.getProblem().createRep()
    model = rep.getModelBase()
    names = {
        model.getCoordinateSet().get(i).getName()
        for i in range(model.getCoordinateSet().getSize())
    }
    assert names == {
        f"{joint}_{dof}"
        for joint, dofs in {
            "lumbar": ("flex", "lateral", "rotate"),
            "hip_l": ("flex", "adduct", "rotate"),
            "hip_r": ("flex", "adduct", "rotate"),
            "knee_l": ("flex",),
            "knee_r": ("flex",),
            "ankle_l": ("flex", "invert"),
            "ankle_r": ("flex", "invert"),
        }.items()
        for dof in dofs
    }
    assert model.getNumControls() == len(names)


@pytest.mark.requires_opensim
@needs_opensim
@pytest.mark.parametrize(
    ("joint", "match"),
    [("knee_r", "cannot weld knee_r_flex"), ("no_such_joint", "unknown joint")],
)
@pytest.mark.unit
def test_reduction_refuses_joints_the_keyframes_move(
    joint: str, match: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match=match):
        create_moco_study(
            TrajectoryConfig(exercise_name="squat", num_mesh_points=5),
            ModelReduction(welded_joints=(joint,)),
        )


@pytest.mark.requires_opensim
@needs_opensim
@pytest.mark.timeout(int(SQUAT_TIME_BUDGET_S) + 60)
def test_reduced_squat_solve_converges_through_keyframes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Headless reduced back-squat solve reaches every keyframe, bottom included."""
    monkeypatch.chdir(tmp_path)
    config = TrajectoryConfig(
        exercise_name="squat",
        num_mesh_points=SQUAT_MESH_INTERVALS,
        max_iterations=SQUAT_MAX_ITERATIONS,
        convergence_tolerance=SQUAT_TOLERANCE,
        constraint_tolerance=SQUAT_TOLERANCE,
    )
    start = time.perf_counter()
    result = solve_trajectory(config, FIXED_PELVIS_STILL_ARMS)
    elapsed = time.perf_counter() - start

    assert result.converged, "Moco did not converge on the reduced squat"
    assert np.isfinite(result.objective_value)
    assert 0 < result.iterations <= SQUAT_MAX_ITERATIONS
    assert elapsed < SQUAT_TIME_BUDGET_S
    # Welded coordinates sit within WELD_KEYFRAME_TOL_RAD of every keyframe by
    # the reduction's precondition; the solved ones are measured here.
    assert WELD_KEYFRAME_TOL_RAD < KEYFRAME_TOL_RAD
    errors = phase_keyframe_errors(
        result, get_exercise_objective("squat"), set(result.coordinates)
    )
    assert errors["bottom"] < KEYFRAME_TOL_RAD, errors
    assert errors["lockout"] < KEYFRAME_TOL_RAD, errors
    assert max(errors.values()) < KEYFRAME_TOL_RAD, errors


@pytest.mark.requires_opensim
@needs_opensim
def test_study_carries_the_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mesh, iteration limit, tolerances, duration and goal weights come from config."""
    monkeypatch.chdir(tmp_path)
    config = TrajectoryConfig(
        exercise_name="squat",
        duration=2.5,
        num_mesh_points=12,
        max_iterations=222,
        convergence_tolerance=3e-5,
        constraint_tolerance=4e-5,
        weight_tracking=8.0,
        weight_effort=1.5,
    )
    study = create_moco_study(config)
    solver = opensim.MocoCasADiSolver.safeDownCast(study.updSolver())
    assert solver.get_num_mesh_intervals() == 12
    assert solver.get_optim_max_iterations() == 222
    assert solver.get_optim_convergence_tolerance() == pytest.approx(3e-5)
    assert solver.get_optim_constraint_tolerance() == pytest.approx(4e-5)
    rep = study.getProblem().createRep()
    assert rep.getTimeInitialBounds().getUpper() == pytest.approx(0.0)
    assert rep.getTimeFinalBounds().getLower() == pytest.approx(2.5)
    weights = {
        rep.getCostByIndex(i).getName(): rep.getCostByIndex(i).getWeight()
        for i in range(rep.getNumCosts())
    }
    assert weights == {"keyframe_tracking": 8.0, "effort": 1.5}
