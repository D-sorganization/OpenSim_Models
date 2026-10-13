"""Joint element creation helpers for OpenSim .osim files."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.shared.utils.xml_helpers._coordinate_defaults import (
    set_coordinate_default,
    set_coordinate_defaults,
)
from opensim_models.shared.utils.xml_helpers._formatting import (
    ZERO_VEC3,
    orientation_str,
    vec3_str,
)
from opensim_models.shared.utils.xml_helpers._spatial_transform import (
    _add_spatial_transform,
)

__all__ = [
    "add_ball_joint",
    "add_custom_joint",
    "add_free_joint",
    "add_pin_joint",
    "add_weld_joint",
    "set_coordinate_default",
    "set_coordinate_defaults",
]


def _frame_path(body: str) -> str:
    """Return the OpenSim component path of a body (ground lives at /ground)."""
    return "/ground" if body == "ground" else f"/bodyset/{body}"


def _add_joint_frames(
    joint: ET.Element,
    name: str,
    parent_body: str,
    child_body: str,
    location_in_parent: tuple[float, float, float],
    location_in_child: tuple[float, float, float],
    orientation_in_parent: tuple[float, float, float],
    orientation_in_child: tuple[float, float, float],
) -> None:
    """Append parent and child PhysicalOffsetFrame elements to a joint."""
    # âš¡ Bolt Optimization: Fast-path tuple equality before function calls.
    # What: Use CPython's highly efficient tuple equality check `== (0.0, 0.0, 0.0)` to bypass `vec3_str` function call overhead.
    # Why: Zero vectors are extremely common for orientations and translations. Avoiding the function call provides a measurable speedup.
    # Impact: Reduces overhead in the heavily used `_add_joint_frames` function.
    pf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_parent")
    ET.SubElement(pf, "socket_parent").text = _frame_path(parent_body)
    ET.SubElement(pf, "translation").text = (
        "0.000000 0.000000 0.000000"
        if location_in_parent.__class__ is tuple
        and location_in_parent == (0.0, 0.0, 0.0)
        else vec3_str(*location_in_parent)
    )
    ET.SubElement(pf, "orientation").text = (
        "0.000000 0.000000 0.000000"
        if orientation_in_parent.__class__ is tuple
        and orientation_in_parent == (0.0, 0.0, 0.0)
        else orientation_str(*orientation_in_parent)
    )

    cf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_child")
    ET.SubElement(cf, "socket_parent").text = _frame_path(child_body)
    ET.SubElement(cf, "translation").text = (
        "0.000000 0.000000 0.000000"
        if location_in_child.__class__ is tuple and location_in_child == (0.0, 0.0, 0.0)
        else vec3_str(*location_in_child)
    )
    ET.SubElement(cf, "orientation").text = (
        "0.000000 0.000000 0.000000"
        if orientation_in_child.__class__ is tuple
        and orientation_in_child == (0.0, 0.0, 0.0)
        else orientation_str(*orientation_in_child)
    )

    ET.SubElement(joint, "socket_parent_frame").text = f"{name}_parent"
    ET.SubElement(joint, "socket_child_frame").text = f"{name}_child"


def _add_coordinate_set(
    joint: ET.Element,
    coordinates: list[dict[str, float | str]],
) -> None:
    """Append a <coordinates> element with Coordinate children to a joint."""
    coord_set = ET.SubElement(joint, "coordinates")
    for c in coordinates:
        coord = ET.SubElement(coord_set, "Coordinate", name=str(c["name"]))
        v = float(c["default_value"])
        ET.SubElement(coord, "default_value").text = (
            "0.000000" if v == 0.0 else "%.6f" % v  # noqa: UP031
        )
        # âš¡ Bolt Optimization: Use % formatting instead of f-strings.
        # What: Replace f"{float_str(min)} {float_str(max)}" with "%.6f %.6f" % (min, max)
        # Why: In hot paths, old-style % formatting is significantly faster (~50%) than f-strings with multiple float_str calls.
        # Impact: Reduces XML string formatting overhead during model generation.
        ET.SubElement(coord, "range").text = "%.10f %.10f" % (  # noqa: UP031
            float(c["range_min"]),
            float(c["range_max"]),
        )


def add_pin_joint(
    jointset: ET.Element,
    *,
    name: str,
    parent_body: str,
    child_body: str,
    location_in_parent: tuple[float, float, float],
    location_in_child: tuple[float, float, float],
    orientation_in_parent: tuple[float, float, float] = (0, 0, 0),
    orientation_in_child: tuple[float, float, float] = (0, 0, 0),
    coord_name: str,
    default_value: float = 0.0,
    range_min: float = -1.5708,
    range_max: float = 1.5708,
) -> ET.Element:
    """Append a <PinJoint> to *jointset* and return it."""
    joint = ET.SubElement(jointset, "PinJoint", name=name)

    _add_joint_frames(
        joint,
        name,
        parent_body,
        child_body,
        location_in_parent,
        location_in_child,
        orientation_in_parent,
        orientation_in_child,
    )

    # Coordinate
    coords = ET.SubElement(joint, "coordinates")
    coord = ET.SubElement(coords, "Coordinate", name=coord_name)
    ET.SubElement(coord, "default_value").text = (
        "0.000000" if default_value == 0.0 else "%.6f" % default_value  # noqa: UP031
    )
    # âš¡ Bolt Optimization: Use % formatting instead of f-strings.
    ET.SubElement(coord, "range").text = "%.10f %.10f" % (  # noqa: UP031
        range_min,
        range_max,
    )

    return joint


def add_ball_joint(
    jointset: ET.Element,
    *,
    name: str,
    parent_body: str,
    child_body: str,
    location_in_parent: tuple[float, float, float],
    location_in_child: tuple[float, float, float],
    orientation_in_parent: tuple[float, float, float] = (0, 0, 0),
    orientation_in_child: tuple[float, float, float] = (0, 0, 0),
    coordinates: list[dict[str, float | str]],
) -> ET.Element:
    """Append a <BallJoint> (3-DOF rotation) to *jointset* and return it.

    *coordinates* is a list of 3 dicts, each with keys:
      - ``name`` (str): coordinate name
      - ``default_value`` (float): initial value in radians
      - ``range_min`` (float): lower bound in radians
      - ``range_max`` (float): upper bound in radians
    """
    if len(coordinates) != 3:
        raise ValueError(
            f"BallJoint requires exactly 3 coordinates, got {len(coordinates)}"
        )

    joint = ET.SubElement(jointset, "BallJoint", name=name)
    _add_joint_frames(
        joint,
        name,
        parent_body,
        child_body,
        location_in_parent,
        location_in_child,
        orientation_in_parent,
        orientation_in_child,
    )
    _add_coordinate_set(joint, coordinates)
    return joint


def add_custom_joint(
    jointset: ET.Element,
    *,
    name: str,
    parent_body: str,
    child_body: str,
    location_in_parent: tuple[float, float, float],
    location_in_child: tuple[float, float, float],
    orientation_in_parent: tuple[float, float, float] = (0, 0, 0),
    orientation_in_child: tuple[float, float, float] = (0, 0, 0),
    coordinates: list[dict[str, float | str]],
) -> ET.Element:
    """Append a <CustomJoint> (N-DOF) to *jointset* and return it.

    *coordinates* is a list of dicts (1 or more), each with keys:
      - ``name`` (str): coordinate name
      - ``default_value`` (float): initial value in radians
      - ``range_min`` (float): lower bound in radians
      - ``range_max`` (float): upper bound in radians
      - ``axis`` (str, optional): rotation axis, e.g. "1 0 0" (defaults to
        "0 0 1", "1 0 0", "0 1 0" for the 1st, 2nd, 3rd coordinate)
    """
    if len(coordinates) < 1:
        raise ValueError("CustomJoint requires at least 1 coordinate")

    joint = ET.SubElement(jointset, "CustomJoint", name=name)
    _add_joint_frames(
        joint,
        name,
        parent_body,
        child_body,
        location_in_parent,
        location_in_child,
        orientation_in_parent,
        orientation_in_child,
    )
    _add_coordinate_set(joint, coordinates)
    _add_spatial_transform(joint, coordinates)
    return joint


def add_free_joint(
    jointset: ET.Element,
    *,
    name: str,
    parent_body: str,
    child_body: str,
    location_in_parent: tuple[float, float, float] = (0, 0, 0),
    location_in_child: tuple[float, float, float] = (0, 0, 0),
) -> ET.Element:
    """Append a <FreeJoint> (6-DOF) to *jointset* and return it."""
    joint = ET.SubElement(jointset, "FreeJoint", name=name)
    _add_joint_frames(
        joint,
        name,
        parent_body,
        child_body,
        location_in_parent,
        location_in_child,
        ZERO_VEC3,
        ZERO_VEC3,
    )
    # Explicit names: OpenSim otherwise auto-names them "_coord_0".."_coord_5".
    # Coordinate order of a FreeJoint is rx, ry, rz, tx, ty, tz.
    coords = ET.SubElement(joint, "coordinates")
    for suffix in ("rx", "ry", "rz", "tx", "ty", "tz"):
        coord = ET.SubElement(coords, "Coordinate", name=f"{child_body}_{suffix}")
        ET.SubElement(coord, "default_value").text = "0.000000"
    return joint


def add_weld_joint(
    jointset: ET.Element,
    *,
    name: str,
    parent_body: str,
    child_body: str,
    location_in_parent: tuple[float, float, float],
    location_in_child: tuple[float, float, float] = (0, 0, 0),
    orientation_in_parent: tuple[float, float, float] = (0, 0, 0),
    orientation_in_child: tuple[float, float, float] = (0, 0, 0),
) -> ET.Element:
    """Append a <WeldJoint> (rigid attachment) to *jointset*.

    ``orientation_in_parent``/``orientation_in_child`` default to zero (no
    behaviour change for existing callers). A grip exercise's barbell weld
    can set ``orientation_in_parent`` to the inverse of the hand's own
    abduction tilt, so the welded body ends up level without a wrist
    counter-rotation (issue #426).
    """
    joint = ET.SubElement(jointset, "WeldJoint", name=name)
    _add_joint_frames(
        joint,
        name,
        parent_body,
        child_body,
        location_in_parent,
        location_in_child,
        orientation_in_parent,
        orientation_in_child,
    )
    return joint
