"""Constraint helpers for OpenSim .osim files.

A rigid body can have only one parent joint in OpenSim's kinematic tree, so a
second rigid attachment (the barbell gripped by the other hand) must be a
``WeldConstraint`` rather than a second ``WeldJoint``.
"""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET

from opensim_models.shared.utils.xml_helpers import orientation_str, vec3_str

logger = logging.getLogger(__name__)


def _add_offset_frame(
    model: ET.Element,
    name: str,
    body: str,
    location: tuple[float, float, float],
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """Add a PhysicalOffsetFrame to the model's ``components`` property."""
    components = model.find("components")
    if components is None:
        components = ET.SubElement(model, "components")
    frame = ET.SubElement(components, "PhysicalOffsetFrame", name=name)
    ET.SubElement(frame, "socket_parent").text = f"/bodyset/{body}"
    ET.SubElement(frame, "translation").text = vec3_str(*location)
    ET.SubElement(frame, "orientation").text = orientation_str(*orientation)


def get_constraint_set(model: ET.Element) -> ET.Element:
    """Return the model's ``ConstraintSet``, creating it when absent."""
    cset = model.find("ConstraintSet")
    if cset is None:
        cset = ET.SubElement(model, "ConstraintSet")
    return cset


def add_coordinate_coupler(
    constraintset: ET.Element,
    *,
    name: str,
    independent: str,
    dependent: str,
    slope: float,
) -> ET.Element:
    """Append a linear ``CoordinateCouplerConstraint`` to *constraintset*.

    Enforces ``dependent = slope * independent`` (no offset). This prescribes
    kinematics only; it is not a force or stiffness element.
    """
    if independent == dependent:
        raise ValueError("CoordinateCouplerConstraint needs two distinct coordinates")
    if not math.isfinite(slope):
        raise ValueError(f"coupler slope must be finite, got {slope}")
    coupler = ET.SubElement(constraintset, "CoordinateCouplerConstraint", name=name)
    ET.SubElement(coupler, "isEnforced").text = "true"
    ET.SubElement(coupler, "independent_coordinate_names").text = independent
    ET.SubElement(coupler, "dependent_coordinate_name").text = dependent
    func = ET.SubElement(coupler, "coupled_coordinates_function")
    lin = ET.SubElement(func, "LinearFunction")
    ET.SubElement(lin, "coefficients").text = f"{slope:.12g} 0"
    return coupler


def add_weld_constraint(
    model: ET.Element,
    *,
    name: str,
    body_1: str,
    body_2: str,
    location_in_body_1: tuple[float, float, float],
    location_in_body_2: tuple[float, float, float],
    orientation_in_body_1: tuple[float, float, float] = (0.0, 0.0, 0.0),
    orientation_in_body_2: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> ET.Element:
    """Append a ``WeldConstraint`` between two bodies to the model.

    The constraint locks offset frames on *body_1* and *body_2* together. It is
    stored in the model's ``ConstraintSet`` (flat here, nested at serialization).

    ``orientation_in_body_1``/``orientation_in_body_2`` default to zero (no
    behaviour change for existing callers). A grip exercise's right-hand
    weld can set ``orientation_in_body_1`` to the inverse of that hand's own
    abduction tilt, so the constraint's orientation row is satisfied without
    a wrist counter-rotation (issue #426).
    """
    if body_1 == body_2:
        raise ValueError("WeldConstraint requires two distinct bodies")
    frame_1, frame_2 = f"{name}_frame1", f"{name}_frame2"
    _add_offset_frame(model, frame_1, body_1, location_in_body_1, orientation_in_body_1)
    _add_offset_frame(model, frame_2, body_2, location_in_body_2, orientation_in_body_2)
    cset = get_constraint_set(model)
    weld = ET.SubElement(cset, "WeldConstraint", name=name)
    ET.SubElement(weld, "socket_frame1").text = f"/{frame_1}"
    ET.SubElement(weld, "socket_frame2").text = f"/{frame_2}"
    return weld
