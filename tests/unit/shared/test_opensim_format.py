"""OpenSim 4.x serialization format helpers (issue #378)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from opensim_models.shared.body import add_foot_contact_spheres
from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.utils.constraint_helpers import add_weld_constraint
from opensim_models.shared.utils.xml_helpers import (
    add_custom_joint,
    add_weld_joint,
    serialize_model,
)
from opensim_models.shared.utils.xml_helpers._formatting import wrap_set_objects


def _coords(*axes: str | None) -> list[dict[str, float | str]]:
    out: list[dict[str, float | str]] = []
    for i, axis in enumerate(axes):
        c: dict[str, float | str] = {
            "name": f"c{i}",
            "default_value": 0.0,
            "range_min": -1.0,
            "range_max": 1.0,
        }
        if axis is not None:
            c["axis"] = axis
        out.append(c)
    return out


def test_set_members_are_nested_in_objects_only_when_serialized() -> None:
    root = ET.Element("OpenSimDocument")
    model = ET.SubElement(root, "Model")
    bodyset = ET.SubElement(model, "BodySet")
    ET.SubElement(bodyset, "Body", name="a")
    wrapped = wrap_set_objects(root)
    assert wrapped.find("Model/BodySet/objects/Body") is not None
    assert bodyset.find("Body") is not None  # input tree untouched
    assert "<objects>" in serialize_model(root)


def test_joint_frames_are_nested_in_frames_when_serialized() -> None:
    root = ET.Element("OpenSimDocument")
    jointset = ET.SubElement(ET.SubElement(root, "Model"), "JointSet")
    add_weld_joint(
        jointset,
        name="w",
        parent_body="ground",
        child_body="b",
        location_in_parent=(0, 0, 0),
    )
    wrapped = wrap_set_objects(root)
    assert wrapped.find(".//WeldJoint/frames/PhysicalOffsetFrame") is not None


def test_custom_joint_writes_six_axes_with_noncollinear_rotations() -> None:
    jointset = ET.Element("JointSet")
    joint = add_custom_joint(
        jointset,
        name="j",
        parent_body="a",
        child_body="b",
        location_in_parent=(0, 0, 0),
        location_in_child=(0, 0, 0),
        coordinates=_coords(None, None),
    )
    axes = joint.findall("SpatialTransform/TransformAxis")
    assert [a.get("name") for a in axes] == [
        "rotation1",
        "rotation2",
        "rotation3",
        "translation1",
        "translation2",
        "translation3",
    ]
    rot = [a.findtext("axis") for a in axes[:3]]
    assert len(set(rot)) == 3
    assert axes[2].find("coordinates") is None  # unused rotation is constant 0


def test_custom_joint_rejects_collinear_axes() -> None:
    with pytest.raises(ValueError, match="collinear"):
        add_custom_joint(
            ET.Element("JointSet"),
            name="j",
            parent_body="a",
            child_body="b",
            location_in_parent=(0, 0, 0),
            location_in_child=(0, 0, 0),
            coordinates=_coords("0 0 1", "0 0 1"),
        )


def test_custom_joint_rejects_more_than_six_coordinates() -> None:
    with pytest.raises(ValueError, match="at most 6"):
        add_custom_joint(
            ET.Element("JointSet"),
            name="j",
            parent_body="a",
            child_body="b",
            location_in_parent=(0, 0, 0),
            location_in_child=(0, 0, 0),
            coordinates=_coords(*[None] * 7),
        )


def test_weld_constraint_adds_frames_and_constraint() -> None:
    model = ET.Element("Model")
    add_weld_constraint(
        model,
        name="grip",
        body_1="hand_r",
        body_2="shaft",
        location_in_body_1=(0, 0, 0),
        location_in_body_2=(0.4, 0, 0),
    )
    assert len(model.findall("components/PhysicalOffsetFrame")) == 2
    weld = model.find("ConstraintSet/WeldConstraint")
    assert weld is not None
    assert weld.findtext("socket_frame1") == "/grip_frame1"


def test_weld_constraint_rejects_same_body() -> None:
    with pytest.raises(ValueError, match="distinct"):
        add_weld_constraint(
            ET.Element("Model"),
            name="x",
            body_1="a",
            body_2="a",
            location_in_body_1=(0, 0, 0),
            location_in_body_2=(0, 0, 0),
        )


def test_foot_contact_spheres_sit_at_sole_in_y_up() -> None:
    spec = BodyModelSpec()
    model = ET.Element("Model")
    add_foot_contact_spheres(model, spec)
    _, foot_len, _ = _seg(spec, "foot")
    for sphere in model.findall("ContactGeometrySet/ContactSphere"):
        x, y, z = (float(v) for v in sphere.findtext("location", "").split())
        assert y == pytest.approx(-foot_len + 0.02)
        assert abs(z) == pytest.approx(0.03)
