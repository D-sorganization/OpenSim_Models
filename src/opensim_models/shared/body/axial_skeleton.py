"""Axial skeleton builder: pelvis, torso, head and their joints.

Handles the central body segments and their inter-connections
(ground-pelvis FreeJoint, lumbar BallJoint, neck PinJoint).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.utils.geometry import (
    cylinder_inertia,
    rectangular_prism_inertia,
)
from opensim_models.shared.utils.xml_helpers import (
    add_ball_joint,
    add_body,
    add_free_joint,
    add_pin_joint,
)

logger = logging.getLogger(__name__)


def add_axial_body(
    bodyset: ET.Element,
    spec: BodyModelSpec,
    seg_name: str,
    bodies: dict[str, ET.Element],
) -> tuple[float, float, float]:
    """Build an axial (non-bilateral) body segment and add to bodyset.

    Returns (mass, length, radius) for the segment.
    """
    mass, length, radius = _seg(spec, seg_name)
    # Pelvis and torso use rectangular prism inertia; head uses cylinder.
    if seg_name in ("pelvis", "torso"):
        inertia = rectangular_prism_inertia(mass, radius * 2, length, radius * 2)
    else:
        inertia = cylinder_inertia(mass, radius, length)

    # Mass center at midpoint for torso/head, at origin for pelvis.
    mc_y = length / 2.0 if seg_name != "pelvis" else 0.0

    bodies[seg_name] = add_body(
        bodyset,
        name=seg_name,
        mass=mass,
        mass_center=(0, mc_y, 0),
        inertia_xx=inertia[0],
        inertia_yy=inertia[1],
        inertia_zz=inertia[2],
    )
    return mass, length, radius


def _compute_pelvis_height(spec: BodyModelSpec, p_len: float) -> float:
    """Derive standing pelvis height from lower-limb segment lengths."""
    _, thigh_len, _ = _seg(spec, "thigh")
    _, shank_len, _ = _seg(spec, "shank")
    _, foot_len, _ = _seg(spec, "foot")
    return thigh_len + shank_len + foot_len + p_len / 2.0


def _add_ground_pelvis_joint(
    jointset: ET.Element,
    pelvis_height: float,
) -> None:
    """Add the 6-DOF FreeJoint connecting the ground to the pelvis."""
    add_free_joint(
        jointset,
        name="ground_pelvis",
        parent_body="ground",
        child_body="pelvis",
        location_in_parent=(0, pelvis_height, 0),
    )


def _add_lumbar_joint(
    jointset: ET.Element,
    p_len: float,
) -> None:
    """Add the 3-DOF BallJoint connecting pelvis to torso."""
    add_ball_joint(
        jointset,
        name="lumbar",
        parent_body="pelvis",
        child_body="torso",
        location_in_parent=(0, p_len / 2.0, 0),
        location_in_child=(0, 0, 0),
        coordinates=[
            {
                "name": "lumbar_flex",
                "default_value": 0.0,
                "range_min": -0.5236,
                "range_max": 0.7854,
            },
            {
                "name": "lumbar_lateral",
                "default_value": 0.0,
                "range_min": -0.5236,
                "range_max": 0.5236,
            },
            {
                "name": "lumbar_rotate",
                "default_value": 0.0,
                "range_min": -0.5236,
                "range_max": 0.5236,
            },
        ],
    )


def _add_neck_joint(
    jointset: ET.Element,
    t_len: float,
) -> None:
    """Add the 1-DOF PinJoint connecting torso to head."""
    add_pin_joint(
        jointset,
        name="neck",
        parent_body="torso",
        child_body="head",
        location_in_parent=(0, t_len, 0),
        location_in_child=(0, 0, 0),
        coord_name="neck_flex",
        range_min=-0.5236,
        range_max=0.5236,
    )


def add_axial_joints(
    jointset: ET.Element,
    spec: BodyModelSpec,
    p_len: float,
    t_len: float,
    *,
    skip_ground_joint: bool,
) -> None:
    """Add the axial skeleton joints (ground-pelvis, lumbar, neck)."""
    pelvis_height = _compute_pelvis_height(spec, p_len)
    logger.debug("Derived pelvis height: %.4f m", pelvis_height)

    if not skip_ground_joint:
        _add_ground_pelvis_joint(jointset, pelvis_height)

    _add_lumbar_joint(jointset, p_len)
    _add_neck_joint(jointset, t_len)
