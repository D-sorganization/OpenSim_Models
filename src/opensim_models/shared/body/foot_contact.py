"""Foot contact sphere generation for ground contact simulation.

Adds 4 contact spheres per foot (8 total) for Hunt-Crossley ground
contact forces. Positions are relative to the foot body's center.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.contact.policy import (
    FOOT_SPHERE_RADIUS,
    foot_contact_offsets,
)
from opensim_models.shared.utils.contact_helpers import add_contact_sphere

logger = logging.getLogger(__name__)


def add_foot_contact_spheres(
    model: ET.Element,
    spec: BodyModelSpec,
) -> None:
    """Add 4 contact spheres per foot (8 total) for ground contact.

    Contact points per foot (``contact.policy.FOOT_CONTACT_POINTS``):
      heel_medial, heel_lateral, toe_medial, toe_lateral -- the corners of
      the parity standard's foot box (#472), relative to the foot body frame.
    """
    _, foot_len, _ = _seg(spec, "foot")
    # OpenSim frames are Y-up: the foot body hangs from the ankle (origin) down
    # to the sole at y = -foot_len, so a sphere resting on the ground has its
    # centre one radius above the sole.
    sole_y = -foot_len + FOOT_SPHERE_RADIUS

    for side in ("l", "r"):
        for point, (x, z) in foot_contact_offsets(side, spec.height).items():
            add_contact_sphere(
                model,
                name=f"foot_{side}_{point}",
                body=f"foot_{side}",
                location=(x, sole_y, z),
                radius=FOOT_SPHERE_RADIUS,
            )
