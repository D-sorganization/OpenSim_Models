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
    # ⚡ Bolt Optimization: Fast-path tuple equality before function calls.
    # What: Use CPython's highly efficient tuple equality check `== (0.0, 0.0, 0.0)` to bypass `vec3_str` function call overhead.
    # Why: Zero vectors are extremely common for mass centers. Avoiding the function call provides a measurable speedup.
    # Impact: Reduces overhead in the heavily used `add_body` function.
    ET.SubElement(body, "mass_center").text = (
        "0.000000 0.000000 0.000000"
        if mass_center.__class__ is tuple and mass_center == (0.0, 0.0, 0.0)
        else vec3_str(*mass_center)
    )

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
        ET.SubElement(body, "inertia").text = (
            f"{inertia_xx:.6f} {inertia_yy:.6f} {inertia_zz:.6f} "
            f"{inertia_xy:.6f} {inertia_xz:.6f} {inertia_yz:.6f}"
        )

    return body


def body_inertial(
    body: ET.Element,
) -> tuple[float, tuple[float, float, float], tuple[float, ...]]:
    """Return ``(mass, mass_center, inertia)`` parsed from a <Body> element.

    ``inertia`` is the six-component ``xx yy zz xy xz yz`` tuple about the
    mass centre, as written by ``add_body``.
    """
    mass = float(body.findtext("mass") or "nan")
    cx, cy, cz = (float(v) for v in (body.findtext("mass_center") or "").split())
    inertia = tuple(float(v) for v in (body.findtext("inertia") or "").split())
    if len(inertia) != 6:
        raise ValueError(f"body {body.get('name')!r} needs six inertia components")
    return mass, (cx, cy, cz), inertia


def scale_body_inertial(body: ET.Element, factor: float) -> None:
    """Scale a <Body>'s mass and central inertia by *factor* in place.

    The mass centre is unchanged. Precondition: ``0 < factor`` and finite.
    """
    if not (factor > 0.0 and factor < float("inf")):
        raise ValueError(f"factor must be positive and finite, got {factor}")
    mass, _, inertia = body_inertial(body)
    mass_el = body.find("mass")
    inertia_el = body.find("inertia")
    if mass_el is None or inertia_el is None:
        raise ValueError(f"body {body.get('name')!r} has no mass or inertia")
    mass_el.text = float_str(mass * factor)
    inertia_el.text = " ".join("%.6f" % (factor * v) for v in inertia)  # noqa: UP031
