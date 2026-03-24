"""XML generation helpers for OpenSim .osim files.

DRY: All bodies, joints, and geometry share these formatting functions
so that XML structure is defined in exactly one place.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


def vec3_str(x: float, y: float, z: float) -> str:
    """Format three floats as a space-separated string for OpenSim XML."""
    return f"{x:.6f} {y:.6f} {z:.6f}"


def vec6_str(r1: float, r2: float, r3: float, t1: float, t2: float, t3: float) -> str:
    """Format six floats (rotation + translation) for OpenSim frames."""
    return f"{r1:.6f} {r2:.6f} {r3:.6f} {t1:.6f} {t2:.6f} {t3:.6f}"


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
        f"{inertia_xx:.6f} {inertia_xy:.6f} {inertia_xz:.6f} "
        f"{inertia_yy:.6f} {inertia_yz:.6f} {inertia_zz:.6f}"
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
    """
    for coord in jointset.iter("Coordinate"):
        if coord.get("name") == coord_name:
            dv = coord.find("default_value")
            if dv is not None:
                dv.text = f"{value:.6f}"
            return

    raise KeyError(f"Coordinate '{coord_name}' not found in model")


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
