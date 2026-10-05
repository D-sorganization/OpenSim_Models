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

_CONTACT_SPHERE_RADIUS = 0.02  # metres


def add_foot_contact_spheres(
    model: ET.Element,
    spec: BodyModelSpec,
) -> None:
    """Add 4 contact spheres per foot (8 total) for ground contact.

    Contact points per foot:
      - heel_medial, heel_lateral, toe_medial, toe_lateral
    Positions are relative to the foot body frame (Y-up), placed at the sole.
    """
    _, foot_len, _ = _seg(spec, "foot")
    # OpenSim frames are Y-up: the foot body hangs from the ankle (origin) down
    # to the sole at y = -foot_len, so a sphere resting on the ground has its
    # centre one radius above the sole. Forward is +X, mediolateral is Z.
    sole_y = -foot_len + _CONTACT_SPHERE_RADIUS

    contact_points = {
        "heel_medial": (-0.08, sole_y, -0.03),
        "heel_lateral": (-0.08, sole_y, 0.03),
        "toe_medial": (0.12, sole_y, -0.03),
        "toe_lateral": (0.12, sole_y, 0.03),
    }

    for side in ("l", "r"):
        for point_name, location in contact_points.items():
            add_contact_sphere(
                model,
                name=f"foot_{side}_{point_name}",
                body=f"foot_{side}",
                location=location,
                radius=_CONTACT_SPHERE_RADIUS,
            )
