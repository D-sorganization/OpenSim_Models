"""Foot contact sphere generation for ground contact simulation.

Adds 4 contact spheres per foot (8 total) for Hunt-Crossley ground
contact forces. Positions are relative to the foot body's center.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.utils.contact_helpers import add_contact_sphere

logger = logging.getLogger(__name__)


def add_foot_contact_spheres(
    model: ET.Element,
    spec: BodyModelSpec,
) -> None:
    """Add 4 contact spheres per foot (8 total) for ground contact.

    Contact points per foot:
      - heel_medial, heel_lateral, toe_medial, toe_lateral
    Positions are relative to the foot body's center, with sole_thickness
    derived from the foot segment radius.
    """
    _, _, foot_radius = _seg(spec, "foot")
    sole_thickness = foot_radius

    contact_points = {
        "heel_medial": (-0.08, -0.03, -sole_thickness),
        "heel_lateral": (-0.08, 0.03, -sole_thickness),
        "toe_medial": (0.12, -0.03, -sole_thickness),
        "toe_lateral": (0.12, 0.03, -sole_thickness),
    }

    for side in ("l", "r"):
        for point_name, location in contact_points.items():
            add_contact_sphere(
                model,
                name=f"foot_{side}_{point_name}",
                body=f"foot_{side}",
                location=location,
                radius=0.02,
            )
