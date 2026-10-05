"""Engine-free checks that free-root models start resting on the ground.

A FreeJoint root left at ``pelvis_ty = 0`` puts the pelvis on the floor, so the
foot contact spheres start about a metre inside the y = 0 half-space (#381).
The generator must instead write a ``pelvis_ty`` default derived from the
model's own geometry. These tests need no OpenSim wheel (Python 3.10 lane).
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.exercises.sit_to_stand.sit_to_stand_model import (
    SitToStandModelBuilder,
)
from opensim_models.shared.body import BodyModelSpec
from opensim_models.shared.body._segment_data import _seg
from opensim_models.shared.body.ground_placement import (
    lowest_contact_height_below_pelvis,
)

FREE_ROOT = [e for e in EXERCISE_BUILDERS if e != "bench_press"]
STANDING = ["squat", "gait"]
TOL = 0.005  # 5 mm


def _model(exercise: str) -> ET.Element:
    root = ET.fromstring(EXERCISE_BUILDERS[exercise]())
    model = root.find("Model")
    assert model is not None
    return model


def _pelvis_ty(model: ET.Element) -> float:
    for coord in model.iter("Coordinate"):
        if coord.get("name") == "pelvis_ty":
            text = coord.findtext("default_value")
            assert text is not None
            return float(text)
    raise AssertionError("pelvis_ty coordinate missing")


@pytest.mark.parametrize("exercise", FREE_ROOT)
def test_free_root_pelvis_ty_default_is_set(exercise: str) -> None:
    ty = _pelvis_ty(_model(exercise))
    assert math.isfinite(ty)
    assert ty > 0.1, "pelvis_ty = 0 puts the feet ~1 m inside the ground"


@pytest.mark.parametrize("exercise", [e for e in FREE_ROOT if e != "sit_to_stand"])
def test_lowest_sphere_surface_touches_ground(exercise: str) -> None:
    model = _model(exercise)
    lowest = _pelvis_ty(model) + lowest_contact_height_below_pelvis(model)
    assert lowest == pytest.approx(0.0, abs=TOL)


@pytest.mark.parametrize("exercise", STANDING)
def test_standing_height_matches_leg_anthropometrics(exercise: str) -> None:
    """Near-neutral stance: pelvis centre sits one full leg plus half pelvis up."""
    spec = BodyModelSpec()
    leg = sum(_seg(spec, s)[1] for s in ("thigh", "shank", "foot"))
    half_pelvis = _seg(spec, "pelvis")[1] / 2.0
    ty = _pelvis_ty(_model(exercise))
    assert ty == pytest.approx(leg + half_pelvis, abs=0.05)
    assert 0.8 < ty < 1.1


def test_sit_to_stand_pelvis_rests_on_the_seat() -> None:
    seat = 0.45
    builder = SitToStandModelBuilder(seat_height=seat)
    root = ET.fromstring(builder.build())
    model = root.find("Model")
    assert model is not None
    half_pelvis = _seg(builder.body_spec, "pelvis")[1] / 2.0
    assert _pelvis_ty(model) == pytest.approx(seat + half_pelvis, abs=1e-6)


def test_bench_press_keeps_welded_pelvis() -> None:
    model = _model("bench_press")
    assert all(c.get("name") != "pelvis_ty" for c in model.iter("Coordinate"))
