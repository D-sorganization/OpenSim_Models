"""Constraint helpers for OpenSim .osim files.

A rigid body can have only one parent joint in OpenSim's kinematic tree, so a
second rigid attachment (the barbell gripped by the other hand) must be a
``WeldConstraint`` rather than a second ``WeldJoint``.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.utils.xml_helpers import vec3_str

logger = logging.getLogger(__name__)


def _add_offset_frame(
    model: ET.Element, name: str, body: str, location: tuple[float, float, float]
) -> None:
    """Add a PhysicalOffsetFrame to the model's ``components`` property."""
    components = model.find("components")
    if components is None:
        components = ET.SubElement(model, "components")
    frame = ET.SubElement(components, "PhysicalOffsetFrame", name=name)
    ET.SubElement(frame, "socket_parent").text = f"/bodyset/{body}"
    ET.SubElement(frame, "translation").text = vec3_str(*location)
    ET.SubElement(frame, "orientation").text = vec3_str(0.0, 0.0, 0.0)


def add_weld_constraint(
    model: ET.Element,
    *,
    name: str,
    body_1: str,
    body_2: str,
    location_in_body_1: tuple[float, float, float],
    location_in_body_2: tuple[float, float, float],
) -> ET.Element:
    """Append a ``WeldConstraint`` between two bodies to the model.

    The constraint locks offset frames on *body_1* and *body_2* together. It is
    stored in the model's ``ConstraintSet`` (flat here, nested at serialization).
    """
    if body_1 == body_2:
        raise ValueError("WeldConstraint requires two distinct bodies")
    frame_1, frame_2 = f"{name}_frame1", f"{name}_frame2"
    _add_offset_frame(model, frame_1, body_1, location_in_body_1)
    _add_offset_frame(model, frame_2, body_2, location_in_body_2)
    cset = model.find("ConstraintSet")
    if cset is None:
        cset = ET.SubElement(model, "ConstraintSet")
    weld = ET.SubElement(cset, "WeldConstraint", name=name)
    ET.SubElement(weld, "socket_frame1").text = f"/{frame_1}"
    ET.SubElement(weld, "socket_frame2").text = f"/{frame_2}"
    return weld
