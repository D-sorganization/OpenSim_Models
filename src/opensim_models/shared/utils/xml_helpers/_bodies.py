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

    # ⚡ Bolt Optimization: Fast-path for diagonal inertia matrices.
    # What: Check if cross terms are zero and use f-strings with pre-formatted zeros.
    # Why: Inertia matrices are almost always diagonal in rigid body models.
    # Impact: Avoids evaluating cross-terms using `float_str`, reducing overhead during model generation.
    if inertia_xy == 0.0 and inertia_xz == 0.0 and inertia_yz == 0.0:
        # ⚡ Bolt Optimization: Use % formatting instead of f-strings.
        ET.SubElement(body, "inertia").text = (
            "%.6f %.6f %.6f 0.000000 0.000000 0.000000"  # noqa: UP031
            % (
                inertia_xx,
                inertia_yy,
                inertia_zz,
            )
        )
    else:
        # ⚡ Bolt Optimization: Use % formatting instead of f-strings.
        # What: Replace f"{float_str(...)} ..." with "%.6f ..." % (...)
        # Why: In hot paths, old-style % formatting is significantly faster than f-strings.
        # Impact: Reduces XML string formatting overhead for inertia elements.
        ET.SubElement(body, "inertia").text = "%.6f %.6f %.6f %.6f %.6f %.6f" % (  # noqa: UP031
            inertia_xx,
            inertia_yy,
            inertia_zz,
            inertia_xy,
            inertia_xz,
            inertia_yz,
        )

    return body
