"""XML generation helpers for OpenSim .osim files.

DRY: Bodies, joints, and formatting defined in one place.
Contact geometry helpers live in ``contact_helpers``."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import NamedTuple

logger = logging.getLogger(__name__)


class Vec3(NamedTuple):
    """Immutable 3-component vector (x, y, z) for OpenSim XML helpers."""

    x: float
    y: float
    z: float


def vec3_str(x: float, y: float, z: float) -> str:
    """Format three floats as a space-separated string for OpenSim XML."""
    return f"{x:.6f} {y:.6f} {z:.6f}"


def vec6_str(rotation: Vec3, translation: Vec3) -> str:
    """Format a rotation Vec3 and translation Vec3 for OpenSim frames.

    Args:
        rotation: Euler angles (r1, r2, r3) in radians.
        translation: Cartesian offsets (t1, t2, t3) in metres.

    Returns:
        Space-separated string of six floats: ``r1 r2 r3 t1 t2 t3``.
    """
    return (
        f"{rotation.x:.6f} {rotation.y:.6f} {rotation.z:.6f} "
        f"{translation.x:.6f} {translation.y:.6f} {translation.z:.6f}"
    )


def add_body(
    bodyset: ET.Element,
    *,
    name: str,
    mass: float,
    mass_center: tuple[float, float, float],
    inertia_xx: float,
    inertia_yy: float,
    inertia_zz: float,
    inertia_xy: float = 0.0,
    inertia_xz: float = 0.0,
    inertia_yz: float = 0.0,
) -> ET.Element:
    """Append a <Body> element to *bodyset* and return it."""
    body = ET.SubElement(bodyset, "Body", name=name)
    ET.SubElement(body, "mass").text = f"{mass:.6f}"
    ET.SubElement(body, "mass_center").text = vec3_str(*mass_center)
    ET.SubElement(body, "inertia").text = (
        f"{inertia_xx:.6f} {inertia_yy:.6f} {inertia_zz:.6f} "
        f"{inertia_xy:.6f} {inertia_xz:.6f} {inertia_yz:.6f}"
    )
    return body


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

    # Parent frame
    pf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_parent")
    ET.SubElement(pf, "socket_parent").text = f"/bodyset/{parent_body}"
    ET.SubElement(pf, "translation").text = vec3_str(*location_in_parent)
    ET.SubElement(pf, "orientation").text = vec3_str(*orientation_in_parent)

    # Child frame
    cf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_child")
    ET.SubElement(cf, "socket_parent").text = f"/bodyset/{child_body}"
    ET.SubElement(cf, "translation").text = vec3_str(*location_in_child)
    ET.SubElement(cf, "orientation").text = vec3_str(*orientation_in_child)

    ET.SubElement(joint, "socket_parent_frame").text = f"{name}_parent"
    ET.SubElement(joint, "socket_child_frame").text = f"{name}_child"

    # Coordinate
    coords = ET.SubElement(joint, "coordinates")
    coord = ET.SubElement(coords, "Coordinate", name=coord_name)
    ET.SubElement(coord, "default_value").text = f"{default_value:.6f}"
    ET.SubElement(coord, "range").text = f"{range_min:.6f} {range_max:.6f}"

    return joint


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
    pf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_parent")
    ET.SubElement(pf, "socket_parent").text = f"/bodyset/{parent_body}"
    ET.SubElement(pf, "translation").text = vec3_str(*location_in_parent)
    ET.SubElement(pf, "orientation").text = vec3_str(*orientation_in_parent)

    cf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_child")
    ET.SubElement(cf, "socket_parent").text = f"/bodyset/{child_body}"
    ET.SubElement(cf, "translation").text = vec3_str(*location_in_child)
    ET.SubElement(cf, "orientation").text = vec3_str(*orientation_in_child)

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
        ET.SubElement(coord, "default_value").text = f"{float(c['default_value']):.6f}"
        ET.SubElement(
            coord, "range"
        ).text = f"{float(c['range_min']):.6f} {float(c['range_max']):.6f}"


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


def _add_spatial_transform(
    joint: ET.Element,
    coordinates: list[dict[str, float | str]],
) -> None:
    """Append a <SpatialTransform> with TransformAxis elements to a CustomJoint."""
    spatial = ET.SubElement(joint, "SpatialTransform")
    rotation_axes = ["rotation1", "rotation2", "rotation3"]
    translation_axes = ["translation1", "translation2", "translation3"]

    for i, c in enumerate(coordinates):
        axis_name = rotation_axes[i] if i < 3 else translation_axes[i - 3]
        ta = ET.SubElement(spatial, "TransformAxis", name=axis_name)
        ET.SubElement(ta, "coordinates").text = str(c["name"])
        ET.SubElement(ta, "axis").text = str(c.get("axis", "0 0 1"))


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
      - ``axis`` (str, optional): rotation axis, e.g. "1 0 0" (defaults to "0 0 1")
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

    pf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_parent")
    ET.SubElement(pf, "socket_parent").text = f"/bodyset/{parent_body}"
    ET.SubElement(pf, "translation").text = vec3_str(*location_in_parent)
    ET.SubElement(pf, "orientation").text = vec3_str(0, 0, 0)

    cf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_child")
    ET.SubElement(cf, "socket_parent").text = f"/bodyset/{child_body}"
    ET.SubElement(cf, "translation").text = vec3_str(*location_in_child)
    ET.SubElement(cf, "orientation").text = vec3_str(0, 0, 0)

    ET.SubElement(joint, "socket_parent_frame").text = f"{name}_parent"
    ET.SubElement(joint, "socket_child_frame").text = f"{name}_child"

    return joint


def add_weld_joint(
    jointset: ET.Element,
    *,
    name: str,
    parent_body: str,
    child_body: str,
    location_in_parent: tuple[float, float, float],
    location_in_child: tuple[float, float, float] = (0, 0, 0),
) -> ET.Element:
    """Append a <WeldJoint> (rigid attachment) to *jointset*."""
    joint = ET.SubElement(jointset, "WeldJoint", name=name)

    pf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_parent")
    ET.SubElement(pf, "socket_parent").text = f"/bodyset/{parent_body}"
    ET.SubElement(pf, "translation").text = vec3_str(*location_in_parent)
    ET.SubElement(pf, "orientation").text = vec3_str(0, 0, 0)

    cf = ET.SubElement(joint, "PhysicalOffsetFrame", name=f"{name}_child")
    ET.SubElement(cf, "socket_parent").text = f"/bodyset/{child_body}"
    ET.SubElement(cf, "translation").text = vec3_str(*location_in_child)
    ET.SubElement(cf, "orientation").text = vec3_str(0, 0, 0)

    ET.SubElement(joint, "socket_parent_frame").text = f"{name}_parent"
    ET.SubElement(joint, "socket_child_frame").text = f"{name}_child"

    return joint


def set_coordinate_default(jointset: ET.Element, coord_name: str, value: float) -> None:
    """Set the default_value for a named Coordinate in the JointSet.

    Searches all joints for a Coordinate element whose 'name' attribute matches
    *coord_name* and updates its default_value text.

    Raises:
        ValueError: If *coord_name* is not found in any joint in the JointSet.
    """
    for coord in jointset.iter("Coordinate"):
        if coord.get("name") == coord_name:
            dv = coord.find("default_value")
            if dv is not None:
                dv.text = f"{value:.6f}"
            return
    raise ValueError(f"Coordinate {coord_name!r} not found in jointset")


def indent_xml(elem: ET.Element, level: int = 0) -> None:
    """Add whitespace indentation to an ElementTree in-place."""
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent
    if level == 0:
        elem.tail = "\n"


def serialize_model(root: ET.Element) -> str:
    """Serialize an OpenSim model ElementTree to a formatted XML string."""
    indent_xml(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
