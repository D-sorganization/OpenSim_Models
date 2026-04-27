"""Vector formatting and XML serialization helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import NamedTuple


ZERO_VEC3: tuple[float, float, float] = (0.0, 0.0, 0.0)


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


def indent_xml(elem: ET.Element, level: int = 0) -> None:
    """Add whitespace indentation to an ElementTree in-place."""
    ET.indent(elem, space="  ", level=level)


def serialize_model(root: ET.Element) -> str:
    """Serialize an OpenSim model ElementTree to a formatted XML string."""
    indent_xml(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
