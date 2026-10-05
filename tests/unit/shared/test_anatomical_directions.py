"""Engine-free checks that every coordinate moves its segment the anatomical way.

Canonical frame (fleet parity standard): X forward, Y left, Z up. OpenSim is
Y-up, so canonical = (x, -z, y): left limbs sit at engine -Z. Positive senses
(issue #383, proposed for Repository_Management#2011):

- flexion about the lateral axis moves the distal segment anteriorly (+X);
  the knee keeps its negative-flexion range, so -knee moves the foot back;
- adduction moves the distal segment medially, internal rotation turns the
  anterior face medially, inversion turns the sole medially (mirrored per side);
- lumbar lateral bend and axial rotation are positive toward the left.

The FK is the generator's own pure-Python pass (``ground_placement``), so these
run without the OpenSim wheel.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.shared.body import BodyModelSpec, create_full_body
from opensim_models.shared.body.ground_placement import (
    _apply,
    _frame_named,
    _pose_in_pelvis,
)

SIDES = {"l": 1.0, "r": -1.0}  # canonical +Y is left
ANGLE = math.radians(60.0)


def _body_model() -> ET.Element:
    model = ET.Element("Model")
    create_full_body(
        ET.SubElement(model, "BodySet"),
        ET.SubElement(model, "JointSet"),
        BodyModelSpec(),
        skip_ground_joint=True,
    )
    return model


def _exercise_model(exercise: str) -> ET.Element:
    model = ET.fromstring(EXERCISE_BUILDERS[exercise]()).find("Model")
    assert model is not None
    return model


def _set(model: ET.Element, values: dict[str, float]) -> None:
    for coord in model.iter("Coordinate"):
        if coord.get("name") in values:
            el = coord.find("default_value")
            assert el is not None
            el.text = repr(values[str(coord.get("name"))])


def _canonical(vec: list[float]) -> tuple[float, float, float]:
    return (vec[0], -vec[2], vec[1])


def _point(
    model: ET.Element, body: str, local: tuple[float, float, float] = (0, 0, 0)
) -> tuple[float, float, float]:
    """Canonical position of *local* (engine coords on *body*) in the pelvis."""
    joints = {
        _frame_named(j, "socket_child_frame").body: j
        for j in model.iter()
        if j.tag.endswith("Joint") and j.tag != "FreeJoint"
    }
    rot, pos = _pose_in_pelvis(body, joints)
    offset = _apply(rot, list(map(float, local)))
    return _canonical([p + o for p, o in zip(pos, offset, strict=True)])


def _direction(
    model: ET.Element, body: str, local: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Canonical direction of the body-fixed vector *local*."""
    tip = _point(model, body, local)
    base = _point(model, body)
    return tuple(t - b for t, b in zip(tip, base, strict=True))  # type: ignore[return-value]


def _moved(
    coord: str, value: float, body: str, local: tuple[float, float, float] = (0, 0, 0)
) -> tuple[float, float, float]:
    """Canonical displacement of a body point when *coord* goes 0 -> *value*."""
    model = _body_model()
    before = _point(model, body, local)
    _set(model, {coord: value})
    after = _point(model, body, local)
    return tuple(a - b for a, b in zip(after, before, strict=True))  # type: ignore[return-value]


@pytest.mark.parametrize("seg", ["thigh", "shank", "foot", "upper_arm", "hand"])
@pytest.mark.parametrize("side", SIDES)
def test_left_limbs_are_at_canonical_plus_y(seg: str, side: str) -> None:
    y = _point(_body_model(), f"{seg}_{side}")[1]
    assert y * SIDES[side] > 0.05, f"{seg}_{side} at canonical y={y:.3f}"


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize(
    ("coord", "body", "sign"),
    [
        ("hip_{s}_flex", "shank_{s}", 1.0),
        ("shoulder_{s}_flex", "forearm_{s}", 1.0),
        ("elbow_{s}_flex", "hand_{s}", 1.0),
        ("knee_{s}_flex", "foot_{s}", -1.0),
    ],
)
def test_limb_flexion_is_sagittal_and_anterior(
    side: str, coord: str, body: str, sign: float
) -> None:
    dx, dy, _ = _moved(coord.format(s=side), sign * ANGLE, body.format(s=side))
    assert sign * dx > 0.1, f"{coord}: distal moved {dx:+.3f} m in X"
    assert abs(dy) < 1e-9, f"{coord}: distal moved {dy:+.3f} m sideways"


def test_hip_flexion_ninety_degrees_puts_knee_forward() -> None:
    """Acceptance for #383: +90 deg hip flexion moves the knee to +X."""
    model = _body_model()
    hip = _point(model, "thigh_l")
    _set(model, {"hip_l_flex": math.pi / 2})
    knee = _point(model, "shank_l")
    assert knee[0] - hip[0] > 0.3
    assert knee[1] == pytest.approx(hip[1], abs=1e-9)
    assert knee[2] == pytest.approx(hip[2], abs=1e-9)


@pytest.mark.parametrize("coord", ["lumbar_flex", "neck_flex"])
def test_trunk_and_neck_flexion_bend_forward(coord: str) -> None:
    dx, dy, _ = _moved(coord, math.radians(20.0), "head", (0, 0.2, 0))
    assert dx > 0.02
    assert abs(dy) < 1e-9


def test_lumbar_lateral_bend_and_rotation_are_positive_to_the_left() -> None:
    _, dy, _ = _moved("lumbar_lateral", math.radians(20.0), "head", (0, 0.2, 0))
    assert dy > 0.02
    model = _body_model()
    _set(model, {"lumbar_rotate": math.radians(20.0)})
    assert _direction(model, "torso", (1, 0, 0))[1] > 0.3


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize(
    ("coord", "body"),
    [("hip_{s}_adduct", "shank_{s}"), ("shoulder_{s}_adduct", "forearm_{s}")],
)
def test_adduction_moves_the_limb_medially(side: str, coord: str, body: str) -> None:
    _, dy, _ = _moved(coord.format(s=side), math.radians(20.0), body.format(s=side))
    assert -SIDES[side] * dy > 0.05, f"{coord}: moved {dy:+.3f} m laterally"


@pytest.mark.parametrize("side", SIDES)
def test_hip_internal_rotation_turns_the_toes_medially(side: str) -> None:
    model = _body_model()
    _set(model, {f"hip_{side}_rotate": math.radians(20.0)})
    toe_y = _direction(model, f"foot_{side}", (1, 0, 0))[1]
    assert -SIDES[side] * toe_y > 0.3


@pytest.mark.parametrize("side", SIDES)
def test_ankle_inversion_turns_the_sole_medially(side: str) -> None:
    model = _body_model()
    _set(model, {f"ankle_{side}_inversion": math.radians(20.0)})
    sole_y = _direction(model, f"foot_{side}", (0, -1, 0))[1]
    assert -SIDES[side] * sole_y > 0.3


@pytest.mark.parametrize("side", SIDES)
def test_medial_contact_spheres_are_nearer_the_midline(side: str) -> None:
    model = _exercise_model("squat")
    _set(model, {c.get("name") or "": 0.0 for c in model.iter("Coordinate")})
    spheres = {s.get("name"): s for s in model.iter("ContactSphere")}

    def y(name: str) -> float:
        sphere = spheres[f"foot_{side}_{name}"]
        local = tuple(float(v) for v in (sphere.findtext("location") or "").split())
        return _point(model, f"foot_{side}", local)[1]  # type: ignore[arg-type]

    for end in ("heel", "toe"):
        assert abs(y(f"{end}_medial")) < abs(y(f"{end}_lateral"))


@pytest.mark.parametrize("exercise", ["deadlift", "snatch", "clean_and_jerk"])
def test_gripped_barbell_lies_along_the_lateral_axis(exercise: str) -> None:
    model = _exercise_model(exercise)
    left = _point(model, "barbell_left_sleeve")
    right = _point(model, "barbell_right_sleeve")
    assert left[1] - right[1] > 1.0, "left sleeve must be at canonical +Y"
    assert left[0] == pytest.approx(right[0], abs=1e-6)
    assert left[2] == pytest.approx(right[2], abs=1e-6)


def test_squat_bar_sits_behind_the_neck_across_the_shoulders() -> None:
    model = _exercise_model("squat")
    _set(model, {c.get("name") or "": 0.0 for c in model.iter("Coordinate")})
    bar = _point(model, "barbell_shaft")
    left = _point(model, "barbell_left_sleeve")
    right = _point(model, "barbell_right_sleeve")
    assert bar[0] < 0.0, "high-bar position is posterior to the torso axis"
    assert left[1] - right[1] > 1.0
