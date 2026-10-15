"""Axial skeleton builder: pelvis, torso, head and their joints.

Handles the central body segments and their inter-connections
(ground-pelvis FreeJoint, 3-DOF lumbar and 1-DOF neck CustomJoints).

Axes (Y-up, X forward, Z lateral with left = -Z): flexion turns about -Z so a
positive value bends the trunk or head forward; lumbar lateral bend (about -X)
and axial rotation (about +Y) are positive toward the left (#383).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.body.lumbar_chain import (
    LUMBAR_MOTIONS,
    LumbarCouplingLaw,
    add_lumbar_chain,
)
from opensim_models.shared.parity.standard import JOINT_LIMITS
from opensim_models.shared.utils.geometry import (
    cylinder_inertia,
    rectangular_prism_inertia,
)
from opensim_models.shared.utils.xml_helpers import (
    add_body,
    add_custom_joint,
    add_free_joint,
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


def _add_ground_pelvis_joint(jointset: ET.Element) -> None:
    """Add the 6-DOF FreeJoint connecting the ground to the pelvis.

    The frames coincide, so ``pelvis_ty`` is the absolute pelvis height. Its
    default is set once the pose and contact spheres exist (``ground_placement``).
    """
    add_free_joint(
        jointset,
        name="ground_pelvis",
        parent_body="ground",
        child_body="pelvis",
    )


def _add_lumbar_joint(
    jointset: ET.Element,
    p_len: float,
) -> None:
    """Add the 3-DOF lumbar CustomJoint connecting pelvis to torso."""
    add_custom_joint(
        jointset,
        name="lumbar",
        parent_body="pelvis",
        child_body="torso",
        location_in_parent=(0, p_len / 2.0, 0),
        location_in_child=(0, 0, 0),
        coordinates=[
            {
                "name": f"lumbar_{motion}",
                "default_value": 0.0,
                "range_min": JOINT_LIMITS[f"lumbar_{motion}"][0],
                "range_max": JOINT_LIMITS[f"lumbar_{motion}"][1],
                "axis": axis,
            }
            for motion, axis in LUMBAR_MOTIONS.items()
        ],
    )


def _add_neck_joint(
    jointset: ET.Element,
    t_len: float,
) -> None:
    """Add the 1-DOF neck CustomJoint connecting torso to head."""
    add_custom_joint(
        jointset,
        name="neck",
        parent_body="torso",
        child_body="head",
        location_in_parent=(0, t_len, 0),
        location_in_child=(0, 0, 0),
        coordinates=[
            {
                "name": "neck_flex",
                "default_value": 0.0,
                "range_min": JOINT_LIMITS["neck_flex"][0],
                "range_max": JOINT_LIMITS["neck_flex"][1],
                "axis": "0 0 -1",
            }
        ],
    )


def add_axial_joints(
    jointset: ET.Element,
    spec: BodyModelSpec,
    p_len: float,
    t_len: float,
    *,
    skip_ground_joint: bool,
    lumbar_chain: LumbarCouplingLaw | None = None,
    constraintset: ET.Element | None = None,
) -> None:
    """Add the axial skeleton joints (ground-pelvis, lumbar, neck).

    With ``lumbar_chain`` the single lumbar joint is replaced by the five-level
    segmental chain, whose couplers go into ``constraintset`` (required then).
    """
    if not skip_ground_joint:
        _add_ground_pelvis_joint(jointset)

    if lumbar_chain is None:
        _add_lumbar_joint(jointset, p_len)
    else:
        if constraintset is None:
            raise ValueError("lumbar_chain requires a constraintset")
        add_lumbar_chain(jointset, constraintset, p_len, lumbar_chain)
    _add_neck_joint(jointset, t_len)
