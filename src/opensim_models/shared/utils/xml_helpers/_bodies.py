"""Body element creation helpers for OpenSim .osim files."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.shared.utils.xml_helpers._formatting import vec3_str


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
