"""FreeJoint -> CustomJoint rewrite that makes the generated models Moco-ready (#470)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.shared.utils.xml_helpers import (
    replace_free_joints_with_custom_joints,
)

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None, reason="opensim is not installed in this Python environment"
)

_FREE_ORDER = ["rx", "ry", "rz", "tx", "ty", "tz"]


def _squat_root() -> ET.Element:
    return ET.fromstring(EXERCISE_BUILDERS["squat"]())


def test_rewrites_pelvis_free_joint_keeping_names_and_defaults() -> None:
    root = _squat_root()
    before = root.find(".//FreeJoint[@name='ground_pelvis']")
    assert before is not None
    defaults = {
        c.get("name"): c.findtext("default_value") for c in before.iter("Coordinate")
    }

    assert replace_free_joints_with_custom_joints(root) == ["ground_pelvis"]

    assert root.find(".//FreeJoint") is None
    joint = root.find(".//CustomJoint[@name='ground_pelvis']")
    assert joint is not None
    after = {
        c.get("name"): c.findtext("default_value") for c in joint.iter("Coordinate")
    }
    assert after == defaults
    axes = joint.findall("SpatialTransform/TransformAxis")
    assert [a.findtext("coordinates") for a in axes] == [
        f"pelvis_{s}" for s in _FREE_ORDER
    ]
    assert [a.findtext("axis") for a in axes] == ["1 0 0", "0 1 0", "0 0 1"] * 2


def test_model_without_free_joint_is_unchanged() -> None:
    root = ET.fromstring(EXERCISE_BUILDERS["bench_press"]())
    before = ET.tostring(root)
    assert replace_free_joints_with_custom_joints(root) == []
    assert ET.tostring(root) == before


def test_rejects_free_joint_with_unexpected_coordinate_order() -> None:
    root = _squat_root()
    joint = root.find(".//FreeJoint")
    assert joint is not None
    first = joint.find(".//Coordinate")
    assert first is not None
    first.set("name", "pelvis_tz_dup")
    with pytest.raises(ValueError, match="FreeJoint order"):
        replace_free_joints_with_custom_joints(root)


def _body_transforms(xml: str, tmp: Path) -> dict[str, np.ndarray]:
    path = tmp / "model.osim"
    path.write_text(xml, encoding="utf-8")
    model = opensim.Model(str(path))
    state = model.initSystem()
    model.realizePosition(state)
    bodies = model.getBodySet()
    out = {}
    for i in range(bodies.getSize()):
        body = bodies.get(i)
        xform = body.getTransformInGround(state)
        rot = xform.R().asMat33()
        p = xform.p()
        out[body.getName()] = np.array(
            [[rot.get(r, c) for c in range(3)] + [p.get(r)] for r in range(3)]
        )
    return out


@pytest.mark.requires_opensim
@needs_opensim
@pytest.mark.parametrize("pose", [None, (0.3, -0.4, 0.5, 0.1, 0.9, -0.2)])
def test_custom_root_places_every_body_like_the_free_joint(
    tmp_path: Path, pose: tuple[float, ...] | None
) -> None:
    """Same coordinate values -> same body poses in ground (rotations and offsets)."""
    root = _squat_root()
    if pose is not None:
        joint = root.find(".//FreeJoint")
        assert joint is not None
        for coord, value in zip(joint.iter("Coordinate"), pose, strict=True):
            coord.find("default_value").text = f"{value:.6f}"  # type: ignore[union-attr]
    free = _body_transforms(ET.tostring(root, encoding="unicode"), tmp_path)
    replace_free_joints_with_custom_joints(root)
    custom = _body_transforms(ET.tostring(root, encoding="unicode"), tmp_path)
    assert free.keys() == custom.keys()
    for name in free:
        np.testing.assert_allclose(custom[name], free[name], atol=1e-9, err_msg=name)
