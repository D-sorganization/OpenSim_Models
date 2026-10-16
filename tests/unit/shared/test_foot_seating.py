"""Feet are seated at the contact-law equilibrium depth (#472, MuJoCo #447).

At zero penetration the smoothed Hertz law carries about 59 N per sphere, far
below the weight, so a model built with the soles flush on the floor sinks at
t = 0. The seated soles sit ``delta`` deep, where the static contact force of
every sphere sums to the supported weight (lifter plus bar).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS, SEATED_EXERCISES
from opensim_models.exercises.gait.gait_model import GaitModelBuilder
from opensim_models.shared.body.foot_seating import (
    contact_heights,
    equilibrium_depth,
    foot_seating_offset,
    lower_foot_contact_spheres,
    supported_weight,
)
from opensim_models.shared.contact import static_normal_force

G = 9.80665
# Depth band for a 1e7 Pa Hertz sphere pair (R = 20 mm) carrying 80-200 kg on
# 4-8 spheres: 3-5 mm. Outside 1-8 mm the seating or the law is wrong.
DEPTH_BAND_M = (1.0e-3, 8.0e-3)


def _model(exercise: str) -> ET.Element:
    model = ET.fromstring(EXERCISE_BUILDERS[exercise]()).find("Model")
    assert model is not None
    return model


def _contact_force(model: ET.Element) -> float:
    return sum(static_normal_force(-h) for h in contact_heights(model).values())


def test_seated_exercises_are_the_free_root_standing_models() -> None:
    assert set(SEATED_EXERCISES) == {
        "squat",
        "deadlift",
        "snatch",
        "clean_and_jerk",
        "gait",
    }


@pytest.mark.parametrize("exercise", SEATED_EXERCISES)
def test_static_contact_force_carries_the_supported_weight(exercise: str) -> None:
    model = _model(exercise)
    # Sphere locations are written to 1 nm: ~1e-3 N of a 784-1961 N weight.
    assert _contact_force(model) == pytest.approx(supported_weight(model), rel=1e-6)


@pytest.mark.parametrize("exercise", SEATED_EXERCISES)
def test_every_stance_sphere_penetration_is_in_band(exercise: str) -> None:
    depths = [-h for h in contact_heights(_model(exercise)).values() if h < 0.0]
    # Both feet stand on the floor in the lifts; gait stands on its right foot.
    assert len(depths) == (4 if exercise == "gait" else 8)
    for depth in depths:
        assert DEPTH_BAND_M[0] < depth < DEPTH_BAND_M[1]


@pytest.mark.parametrize("exercise", SEATED_EXERCISES)
def test_seated_build_has_no_remaining_offset(exercise: str) -> None:
    assert foot_seating_offset(_model(exercise)) == pytest.approx(0.0, abs=1e-8)


def test_supported_weight_counts_lifter_and_bar_not_the_chair() -> None:
    assert supported_weight(_model("deadlift")) == pytest.approx(200.0 * G)
    assert supported_weight(_model("sit_to_stand")) == pytest.approx(80.0 * G)


def test_equilibrium_is_independent_of_current_seating() -> None:
    builder = GaitModelBuilder()
    builder.seat_feet_at_equilibrium = False
    unseated = ET.fromstring(builder.build()).find("Model")
    seated = _model("gait")
    assert unseated is not None
    lowered = foot_seating_offset(unseated)
    assert lowered > DEPTH_BAND_M[0]
    lower_foot_contact_spheres(unseated, lowered)
    assert min(contact_heights(unseated).values()) == pytest.approx(
        min(contact_heights(seated).values()), abs=1e-9
    )


def test_equilibrium_depth_solves_the_law() -> None:
    heights = {"a": 0.0, "b": 0.0, "c": 0.01}
    weight = 400.0
    depth = equilibrium_depth(heights, weight)
    total = sum(static_normal_force(depth - h) for h in heights.values())
    assert total == pytest.approx(weight, rel=1e-9)


def test_equilibrium_depth_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="weight"):
        equilibrium_depth({"a": 0.0}, 0.0)
    with pytest.raises(ValueError, match="contact"):
        equilibrium_depth({}, 100.0)
    with pytest.raises(ValueError, match="equilibrium"):
        equilibrium_depth({"a": 0.0}, 1.0)  # below the zero-depth smoothing force


def test_lowering_rejects_negative_depth() -> None:
    with pytest.raises(ValueError, match="depth"):
        lower_foot_contact_spheres(_model("gait"), -1e-3)
