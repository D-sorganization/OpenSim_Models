"""Full-body musculoskeletal model builder.

Builds a 15-segment body (pelvis, torso, head, bilateral arms and legs)
with appropriate joint types. Anthropometric defaults follow Winter (2009)
for a 50th-percentile male (height=1.75 m, mass=80 kg).

Law of Demeter: exercise modules call create_full_body() and receive
body/joint elements -- they never manipulate segment internals.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.body.axial_skeleton import add_axial_body, add_axial_joints
from opensim_models.shared.body.limb_builders import (
    add_bilateral_ball_joint_limb,
    add_bilateral_custom_joint_limb,
    add_bilateral_limb,
)

logger = logging.getLogger(__name__)


def _add_upper_arm(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    shoulder_y: float,
    shoulder_x: float,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral upper-arm segments with 3-DOF shoulder ball joints."""
    add_bilateral_ball_joint_limb(
        bodyset,
        jointset,
        spec,
        seg_name="upper_arm",
        parent_name="torso",
        parent_offset_y=shoulder_y,
        parent_lateral_x=shoulder_x,
        coord_prefix="shoulder",
        coord_suffixes=("flex", "adduct", "rotate"),
        ranges=(
            (-1.0472, 3.1416),
            (-0.5236, 3.1416),
            (-1.5708, 1.5708),
        ),
        bodies=bodies,
    )


def _add_forearm(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral forearm segments with single-axis elbow pin joints."""
    _, ua_len, _ = _seg(spec, "upper_arm")
    add_bilateral_limb(
        bodyset,
        jointset,
        spec,
        seg_name="forearm",
        parent_name="upper_arm",
        parent_offset_y=-ua_len,
        parent_lateral_x=0,
        coord_prefix="elbow",
        range_min=0,
        range_max=2.618,
        bodies=bodies,
    )


def _add_hand(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral hand segments with 2-DOF wrist custom joints."""
    _, fa_len, _ = _seg(spec, "forearm")
    add_bilateral_custom_joint_limb(
        bodyset,
        jointset,
        spec,
        seg_name="hand",
        parent_name="forearm",
        parent_offset_y=-fa_len,
        parent_lateral_x=0,
        coord_prefix="wrist",
        coord_defs=[
            {
                "suffix": "flex",
                "range_min": -1.2217,
                "range_max": 1.2217,
                "axis": "0 0 1",
            },
            {
                "suffix": "deviation",
                "range_min": -0.3491,
                "range_max": 0.5236,
                "axis": "1 0 0",
            },
        ],
        bodies=bodies,
    )


def _add_upper_limbs(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    t_len: float,
    t_rad: float,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral upper-limb segments (arms, forearms, hands)."""
    shoulder_y = t_len * 0.95
    shoulder_x = t_rad * 1.2
    _add_upper_arm(bodyset, jointset, spec, shoulder_y, shoulder_x, bodies)
    _add_forearm(bodyset, jointset, spec, bodies)
    _add_hand(bodyset, jointset, spec, bodies)


def _add_thigh(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    p_len: float,
    hip_x: float,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral thigh segments with 3-DOF hip ball joints."""
    add_bilateral_ball_joint_limb(
        bodyset,
        jointset,
        spec,
        seg_name="thigh",
        parent_name="pelvis",
        parent_offset_y=-p_len / 2.0,
        parent_lateral_x=hip_x,
        coord_prefix="hip",
        coord_suffixes=("flex", "adduct", "rotate"),
        ranges=(
            (-0.5236, 2.0944),
            (-0.7854, 0.5236),
            (-0.7854, 0.7854),
        ),
        bodies=bodies,
    )


def _add_shank(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral shank segments with single-axis knee pin joints."""
    _, th_len, _ = _seg(spec, "thigh")
    add_bilateral_limb(
        bodyset,
        jointset,
        spec,
        seg_name="shank",
        parent_name="thigh",
        parent_offset_y=-th_len,
        parent_lateral_x=0,
        coord_prefix="knee",
        range_min=-2.618,
        range_max=0,
        bodies=bodies,
    )


def _add_foot(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral foot segments with 2-DOF ankle custom joints."""
    _, sh_len, _ = _seg(spec, "shank")
    add_bilateral_custom_joint_limb(
        bodyset,
        jointset,
        spec,
        seg_name="foot",
        parent_name="shank",
        parent_offset_y=-sh_len,
        parent_lateral_x=0,
        coord_prefix="ankle",
        coord_defs=[
            {
                "suffix": "flex",
                "range_min": -0.3491,
                "range_max": 0.8727,
                "axis": "0 0 1",
            },
            {
                "suffix": "inversion",
                "range_min": -0.3491,
                "range_max": 0.3491,
                "axis": "1 0 0",
            },
        ],
        bodies=bodies,
    )


def _add_lower_limbs(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    p_len: float,
    p_rad: float,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral lower-limb segments (thighs, shanks, feet)."""
    hip_x = p_rad * 0.6
    _add_thigh(bodyset, jointset, spec, p_len, hip_x, bodies)
    _add_shank(bodyset, jointset, spec, bodies)
    _add_foot(bodyset, jointset, spec, bodies)


def create_full_body(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec | None = None,
    *,
    skip_ground_joint: bool = False,
) -> dict[str, ET.Element]:
    """Build the full-body model and append bodies/joints to the given sets.

    Args:
        bodyset: XML element to append Body elements to.
        jointset: XML element to append Joint elements to.
        spec: Anthropometric specification (defaults to 50th-percentile male).
        skip_ground_joint: When True, the FreeJoint connecting pelvis to ground
            is omitted (use when another joint provides the pelvis parent).

    Returns dict of body name -> ET.Element for all created bodies.
    """
    if spec is None:
        spec = BodyModelSpec()

    logger.info(
        "Building full-body model (mass=%.1f kg, height=%.2f m)",
        spec.total_mass,
        spec.height,
    )

    bodies: dict[str, ET.Element] = {}

    # --- Axial skeleton (pelvis, torso, head) ---
    _, p_len, p_rad = add_axial_body(bodyset, spec, "pelvis", bodies)
    _, t_len, t_rad = add_axial_body(bodyset, spec, "torso", bodies)
    add_axial_body(bodyset, spec, "head", bodies)
    add_axial_joints(jointset, spec, p_len, t_len, skip_ground_joint=skip_ground_joint)

    # --- Upper limbs ---
    _add_upper_limbs(bodyset, jointset, spec, t_len, t_rad, bodies)

    # --- Lower limbs ---
    _add_lower_limbs(bodyset, jointset, spec, p_len, p_rad, bodies)

    logger.info("Full-body model complete: %d bodies created", len(bodies))
    return bodies
