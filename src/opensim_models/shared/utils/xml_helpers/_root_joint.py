"""FreeJoint -> CustomJoint rewrite for solvers that reject FreeJoints (#470).

OpenSim Moco refuses a ``FreeJoint`` because its generalized speeds are not
the time derivatives of its coordinates (``qdot != u``).  A ``CustomJoint``
with rotations about X, Y, Z (composed body-fixed, in order) followed by
translations along the parent X, Y, Z axes places the child frame exactly as
the FreeJoint's body-fixed X-Y-Z angles and parent-frame translation do, under
the same coordinate names, so goals, bounds and states keyed by coordinate
name carry over unchanged.

Design by Contract:
    - Preconditions: each FreeJoint has exactly six coordinates in the
      FreeJoint order ``rx, ry, rz, tx, ty, tz``; otherwise ValueError.
    - Postconditions: the tree has no FreeJoint left; every rewritten joint
      keeps its name, frames, coordinate names and default values.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.shared.utils.xml_helpers._spatial_transform import (
    _add_spatial_transform,
)

_FREE_SUFFIXES: tuple[str, ...] = ("rx", "ry", "rz", "tx", "ty", "tz")
_FREE_AXES: tuple[str, ...] = ("1 0 0", "0 1 0", "0 0 1") * 2


def _free_coordinate_names(joint: ET.Element) -> list[str]:
    """Coordinate names of *joint*, checked against the FreeJoint order."""
    names = [str(c.get("name")) for c in joint.iter("Coordinate")]
    suffixes = tuple(name.rsplit("_", 1)[-1] for name in names)
    if suffixes != _FREE_SUFFIXES:
        raise ValueError(
            f"FreeJoint {joint.get('name')!r} coordinates {names} are not in "
            f"the FreeJoint order {list(_FREE_SUFFIXES)}"
        )
    return names


def replace_free_joints_with_custom_joints(root: ET.Element) -> list[str]:
    """Rewrite every ``FreeJoint`` under *root* as an equivalent CustomJoint.

    Returns:
        Names of the rewritten joints (empty when the model has none).

    Raises:
        ValueError: A FreeJoint's coordinates are not ``*_rx .. *_tz``.
    """
    rewritten: list[str] = []
    for joint in list(root.iter("FreeJoint")):
        names = _free_coordinate_names(joint)
        joint.tag = "CustomJoint"
        _add_spatial_transform(
            joint,
            [
                {"name": name, "axis": axis}
                for name, axis in zip(names, _FREE_AXES, strict=True)
            ],
        )
        rewritten.append(str(joint.get("name")))
    if root.find(".//FreeJoint") is not None:
        raise AssertionError("postcondition: a FreeJoint survived the rewrite")
    return rewritten
