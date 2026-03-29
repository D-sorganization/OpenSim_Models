"""Design-by-Contract postcondition checks.

Used to validate outputs after computation — catches bugs in model
generation before they propagate to downstream XML or simulation.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


def ensure_valid_xml(xml_string: str) -> ET.Element:
    """Parse *xml_string* and return the root element.

    Raises ValueError if the string is not well-formed XML.
    """
    try:
        return ET.fromstring(xml_string)  # nosec B314 — parsing self-generated XML
    except ET.ParseError as exc:
        raise ValueError(f"Generated XML is not well-formed: {exc}") from exc


def ensure_coordinates_within_bounds(root: ET.Element) -> None:
    """Verify every Coordinate's default_value is within its declared range.

    DbC: catches mismatches between set_initial_pose() values and the
    range limits declared when the joint was created (issue #52).

    Raises ValueError if any default is out of range (with 1e-6 tolerance).
    """
    tol = 1e-6
    for coord in root.iter("Coordinate"):
        name = coord.get("name", "<unnamed>")
        dv_el = coord.find("default_value")
        rng_el = coord.find("range")
        if dv_el is None or rng_el is None:
            continue
        default = float(dv_el.text)  # type: ignore[arg-type]
        parts = rng_el.text.split()  # type: ignore[union-attr]
        lo, hi = float(parts[0]), float(parts[1])
        if default < lo - tol or default > hi + tol:
            raise ValueError(
                f"Coordinate '{name}' default_value {default:.6f} "
                f"is outside range [{lo:.6f}, {hi:.6f}]"
            )


def ensure_positive_mass(mass: float, body_name: str) -> None:
    """Assert that a body's mass is positive after computation."""
    if mass <= 0:
        raise ValueError(
            f"Postcondition violated: {body_name} mass={mass} is not positive"
        )


def ensure_positive_definite_inertia(
    ixx: float, iyy: float, izz: float, body_name: str
) -> None:
    """Assert that principal inertias are positive (necessary for PD)."""
    for label, val in [("Ixx", ixx), ("Iyy", iyy), ("Izz", izz)]:
        if val <= 0:
            raise ValueError(
                f"Postcondition violated: {body_name} {label}={val} not positive"
            )
    # Triangle inequality for principal inertias
    if ixx + iyy < izz or ixx + izz < iyy or iyy + izz < ixx:
        raise ValueError(
            f"Postcondition violated: {body_name} inertias "
            f"({ixx}, {iyy}, {izz}) violate triangle inequality"
        )
