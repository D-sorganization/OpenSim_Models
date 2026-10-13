# SPDX-License-Identifier: MIT
"""Marker set helpers for OpenSim models (#387).

Builds a standard MarkerSet for an OpenSim Model, placing markers on the
canonical anatomical segments (pelvis, torso, head, limbs) and equipment (bar)
derived from the BodyModelSpec geometry.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.utils.xml_helpers import vec3_str

logger = logging.getLogger(__name__)


def add_marker(
    markerset: ET.Element,
    *,
    name: str,
    body: str,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    fixed: bool = True,
) -> ET.Element:
    """Add a Marker element to an OpenSim MarkerSet.

    Args:
        markerset: Target MarkerSet element.
        name: Unique name for the marker.
        body: Parent body name within the model's BodySet.
        location: (x, y, z) coordinates in metres relative to the parent body frame.
        fixed: Whether the marker location is fixed on the body (default True).

    Returns:
        The created Marker XML element.
    """
    marker = ET.SubElement(markerset, "Marker", name=name)
    ET.SubElement(marker, "socket_parent_frame").text = f"/bodyset/{body}"
    ET.SubElement(marker, "location").text = vec3_str(*location)
    ET.SubElement(marker, "fixed").text = "true" if fixed else "false"
    return marker


def add_standard_markers(
    model: ET.Element,
    spec: BodyModelSpec,
    *,
    uses_barbell: bool = True,
) -> ET.Element:
    """Add standard anatomical and equipment markers to an OpenSim model.

    Populates a `<MarkerSet>` with canonical anatomical markers placed on:
    - pelvis (at origin)
    - torso (at C7 / top of torso)
    - head (at top of head)
    - bilateral limbs (distal joints: elbow, wrist, hand, knee, ankle, foot)
    - barbell shaft (if uses_barbell is True)

    Args:
        model: Root Model element.
        spec: Body model specifications for anthropometric dimensions.
        uses_barbell: Whether to include the barbell marker.

    Returns:
        The populated MarkerSet element.
    """
    markerset = model.find("MarkerSet")
    if markerset is None:
        markerset = ET.SubElement(model, "MarkerSet", name="markerset")

    # Pelvis
    add_marker(markerset, name="pelvis", body="pelvis", location=(0.0, 0.0, 0.0))

    # Torso (at C7 / neck junction, length along +Y)
    _, torso_len, _ = _seg(spec, "torso")
    add_marker(markerset, name="torso", body="torso", location=(0.0, torso_len, 0.0))

    # Head (top of head, length along +Y)
    _, head_len, _ = _seg(spec, "head")
    add_marker(markerset, name="head", body="head", location=(0.0, head_len, 0.0))

    # Appendicular upper and lower limbs (bilateral)
    limb_segments: tuple[str, ...] = (
        "upper_arm",
        "forearm",
        "hand",
        "thigh",
        "shank",
        "foot",
    )
    for seg in limb_segments:
        _, seg_len, _ = _seg(spec, seg)
        for side in ("l", "r"):
            body_name = f"{seg}_{side}"
            # Distal end of each limb segment along -Y
            add_marker(
                markerset,
                name=body_name,
                body=body_name,
                location=(0.0, -seg_len, 0.0),
            )

    # Barbell shaft
    if uses_barbell:
        add_marker(
            markerset,
            name="bar",
            body="barbell_shaft",
            location=(0.0, 0.0, 0.0),
        )

    logger.debug("Added standard markers to MarkerSet")
    return markerset
