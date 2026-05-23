"""Body element creation helpers for OpenSim .osim files."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.shared.utils.xml_helpers._formatting import float_str, vec3_str


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
    ET.SubElement(body, "mass").text = float_str(mass)
    ET.SubElement(body, "mass_center").text = vec3_str(*mass_center)
    ET.SubElement(body, "inertia").text = (
        f"{float_str(inertia_xx)} {float_str(inertia_yy)} {float_str(inertia_zz)} "
        f"{float_str(inertia_xy)} {float_str(inertia_xz)} {float_str(inertia_yz)}"
    )
    return body
