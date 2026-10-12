"""The lift objectives consume the vendored exercise spec (standard v2.1).

UpstreamDrift#11742 (LIFT-2), Repository_Management#2060 (Option A): phase
names, phase timing, phase descriptions and the start, catch and lockout
via-poses come from the vendored ``biomech_parity_standard.json``, never from
pack-local tables.  Engine-free: runs without the opensim wheel.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.optimization import spec_lifts
from opensim_models.optimization._types import ExerciseObjective, Phase
from opensim_models.optimization.exercise_objectives import get_exercise_objective
from opensim_models.shared.parity._canonical import conformance, spec
from opensim_models.shared.parity.aliases import engine_name

STD = conformance.load_standard()
LIFTS = ("squat", "deadlift", "bench_press", "snatch", "clean_and_jerk")

# sha256 of Repository_Management/shared_scripts/model_parity/
# biomech_parity_standard.json at v2.1.0 (Repository_Management#2079, 4c033bf).
RM_STANDARD_V2_1_SHA256 = (
    "a0eb6c2bbbfeb70011bad62cf6d21a9245ffabce757c390633b516f542eb3ef8"
)


def _full_pose(exercise: str, pose: str) -> dict[str, float]:
    """Every coordinate of a via-pose under its OpenSim name; unlisted ones 0."""
    out = dict.fromkeys(conformance.expected_coordinates(STD), 0.0)
    out.update(spec.pose_coordinates(STD, exercise, pose))
    return {engine_name(name): value for name, value in out.items()}


def _phase(objective: ExerciseObjective, name: str) -> Phase:
    return next(p for p in objective.phases if p.name == name)


def test_vendored_standard_is_repository_management_v2_1() -> None:
    assert conformance.standard_sha256() == RM_STANDARD_V2_1_SHA256
    assert STD["version"] == "2.1.0"


ALL_EXERCISES = (
    "squat",
    "deadlift",
    "bench_press",
    "snatch",
    "clean_and_jerk",
    "gait",
    "sit_to_stand",
)


@pytest.mark.parametrize("exercise", ALL_EXERCISES)
def test_phases_come_from_spec(exercise: str) -> None:
    objective = get_exercise_objective(exercise)
    want = spec.exercise_spec(STD, exercise)["phases"]
    assert [p.name for p in objective.phases] == [p["name"] for p in want]
    assert [p.time_fraction for p in objective.phases] == [p["t_frac"] for p in want]
    assert [p.description for p in objective.phases] == [p["definition"] for p in want]


@pytest.mark.parametrize("exercise", ("gait", "sit_to_stand"))
def test_functional_movement_phases_conform_to_spec(exercise: str) -> None:
    """Fingerprint phase names match spec and ledger entry is removed (#434)."""
    objective = get_exercise_objective(exercise)
    names = [p.name for p in objective.phases]
    assert names == spec.phase_names(STD, exercise)
    fp = {"exercise": exercise, "phase_names": names}
    assert spec.check_fingerprint(fp, STD) == []
    ledger = conformance.load_ledger(
        Path(conformance.__file__).parents[1] / "parity_divergences.json"
    )
    assert "phase_names" not in ledger.get("divergences", {})


@pytest.mark.parametrize("exercise", LIFTS)
def test_anchored_phases_hold_their_via_pose(exercise: str) -> None:
    objective = get_exercise_objective(exercise)
    poses = spec.exercise_spec(STD, exercise)["via_poses"]
    anchors = spec_lifts.anchors(exercise)
    assert set(anchors) == set(poses)
    assert anchors == {p: spec.via_pose_phase(STD, exercise, p) for p in poses}
    assert anchors["start"] == spec.phase_names(STD, exercise)[0]
    for pose, phase in anchors.items():
        assert _phase(objective, phase).joint_targets == _full_pose(exercise, pose)


@pytest.mark.parametrize("exercise", LIFTS)
def test_every_target_is_a_generated_model_coordinate(exercise: str) -> None:
    """Phase keys resolve to coordinates of the generated model (#414)."""
    root = ET.fromstring(EXERCISE_BUILDERS[exercise]())
    coordinates = {c.get("name", "") for c in root.iter("Coordinate")}
    objective = get_exercise_objective(exercise)
    for phase in objective.phases:
        assert set(phase.joint_targets) <= coordinates, phase.name
    assert set(objective.primary_coordinates) <= coordinates


def test_unanchored_phase_is_the_blend_of_its_anchors() -> None:
    """Deadlift first_pull (t 0.10) lies between setup (0) and lockout (0.65)."""
    objective = get_exercise_objective("deadlift")
    start, lockout = _full_pose("deadlift", "start"), _full_pose("deadlift", "lockout")
    w = 0.1 / 0.65
    got = _phase(objective, "first_pull").joint_targets
    for name, value in got.items():
        assert value == pytest.approx(start[name] + w * (lockout[name] - start[name]))
    # After the last anchor the target holds the last anchored pose.
    assert _phase(objective, "descent").joint_targets == lockout


def test_unknown_exercise_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown exercise"):
        spec_lifts.lift_objective("curl", description="", primary_coordinates=())


def test_unknown_primary_coordinate_is_rejected() -> None:
    with pytest.raises(ValueError, match="primary coordinates"):
        spec_lifts.lift_objective(
            "squat", description="", primary_coordinates=("hip_flexion",)
        )
