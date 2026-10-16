"""Contact policy: names and defaults come from the parity standard (#472)."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises.gait.gait_model import GaitModelBuilder
from opensim_models.shared.body import BodyModelSpec, add_foot_contact_spheres
from opensim_models.shared.contact import (
    FOOT_CONTACT_POINTS,
    FOOT_SPHERE_RADIUS,
    GROUND_FRICTION,
    foot_contact_offsets,
    foot_sphere_names,
    static_normal_force,
)
from opensim_models.shared.contact.policy import (
    CONSTANT_CONTACT_FORCE,
    HERTZ_SMOOTHING,
)
from opensim_models.shared.parity._canonical import conformance

STANDARD = conformance.load_standard()
FOOT_BOX = STANDARD["contact"]["foot_box_m"]


def test_ground_friction_is_the_bundle_value() -> None:
    assert STANDARD["contact"]["ground_friction"] == GROUND_FRICTION


def test_sphere_names_cover_both_feet_in_point_order() -> None:
    names = foot_sphere_names()
    assert names[:4] == [f"foot_l_{p}" for p in FOOT_CONTACT_POINTS]
    assert names[4:] == [f"foot_r_{p}" for p in FOOT_CONTACT_POINTS]


@pytest.mark.parametrize("side", ["l", "r"])
def test_footprint_is_the_standard_foot_box(side: str) -> None:
    points = foot_contact_offsets(side, STANDARD["anthropometrics"]["height_m"])
    xs = sorted({x for x, _ in points.values()})
    zs = sorted({z for _, z in points.values()})
    assert xs[1] - xs[0] == pytest.approx(FOOT_BOX["length"])
    assert zs[1] - zs[0] == pytest.approx(FOOT_BOX["width"])
    # Centred on mid-foot, which the pose frame puts -ankle_x_m ahead of the ankle.
    mid = 0.5 * (xs[0] + xs[1])
    assert mid == pytest.approx(-STANDARD["pose_frame"]["ankle_x_m"])
    lateral = 1.0 if side == "r" else -1.0
    assert math.copysign(1.0, points["heel_lateral"][1]) == lateral
    assert points["toe_medial"][0] > points["heel_medial"][0]


def test_footprint_rejects_bad_side_and_height() -> None:
    with pytest.raises(ValueError, match="side"):
        foot_contact_offsets("x", 1.75)
    with pytest.raises(ValueError, match="height_m"):
        foot_contact_offsets("l", 0.0)


def test_spheres_are_built_on_the_policy_footprint() -> None:
    spec = BodyModelSpec()
    model = ET.Element("Model")
    add_foot_contact_spheres(model, spec)
    spheres = model.findall("ContactGeometrySet/ContactSphere")
    assert [s.get("name") for s in spheres] == foot_sphere_names()
    for sphere in spheres:
        _, side, point = str(sphere.get("name")).split("_", 2)
        x, _, z = (float(v) for v in sphere.findtext("location", "").split())
        assert (x, z) == pytest.approx(foot_contact_offsets(side, spec.height)[point])
        assert float(sphere.findtext("radius", "")) == FOOT_SPHERE_RADIUS


def test_every_foot_force_uses_the_policy_friction_and_smoothing() -> None:
    root = ET.fromstring(GaitModelBuilder().build())
    forces = root.findall(".//SmoothSphereHalfSpaceForce")
    assert len(forces) == len(foot_sphere_names())
    for force in forces:
        assert float(force.findtext("static_friction", "")) == GROUND_FRICTION["static"]
        assert (
            float(force.findtext("dynamic_friction", "")) == GROUND_FRICTION["dynamic"]
        )
        assert float(force.findtext("constant_contact_force", "")) == (
            CONSTANT_CONTACT_FORCE
        )
        assert float(force.findtext("hertz_smoothing", "")) == HERTZ_SMOOTHING


def test_static_normal_force_is_positive_and_monotonic() -> None:
    depths = [-0.01, 0.0, 0.001, 0.002, 0.005]
    forces = [static_normal_force(d) for d in depths]
    assert all(f > 0 for f in forces)
    assert forces == sorted(forces)


def test_static_normal_force_matches_the_closed_form_at_zero_depth() -> None:
    # 4/3 k sqrt(R k) cf^(3/4) / 2 with k = stiffness^(2/3) / 2.
    k = 0.5 * 1.0e7 ** (2.0 / 3.0)
    expected = (4 / 3) * k * math.sqrt(0.02 * k) * CONSTANT_CONTACT_FORCE**0.75 / 2
    assert static_normal_force(0.0) == pytest.approx(expected, rel=1e-12)


def test_static_normal_force_rejects_non_finite_depth() -> None:
    with pytest.raises(ValueError, match="finite"):
        static_normal_force(math.nan)
