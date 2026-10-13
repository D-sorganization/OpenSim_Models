"""Appendicular skeleton (upper and lower limbs) builder.

Constructs bilateral arms, forearms, hands, thighs, shanks, and feet
with appropriate joint types and coordinate ranges.
Extracted from body_model.py to stay under the 300-line monolith budget.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.body.limb_builders import (
    add_bilateral_custom_joint_limb,
    add_bilateral_limb,
)

# Right-side axes of a 3-DOF limb root (hip, shoulder) in the Y-up, X-forward,
# Z-lateral body frame: flexion about Z (distal segment forward), adduction
# about X (medial) and long-axis rotation about Y (internal). The last two are
# mirrored on the left so equal values give a symmetric pose (#383).
_FLEX_AXIS = "0 0 1"
_ADDUCT_AXIS = "1 0 0"
_ROTATE_AXIS = "0 1 0"

# shoulder_{side}_adduct: positive = adduction (toward the midline), negative
# = abduction -- confirmed empirically with real-OpenSim forward kinematics
# (#424: perturbing shoulder_l_adduct/shoulder_r_adduct +-0.2 rad from the
# neutral squat pose and reading hand_l/hand_r position in the ground frame).
# Shoulder abduction active ROM reaches ~180 deg (arm overhead), while
# adduction across the body is capped around 30 deg (Kapandji, *The
# Physiology of the Joints*, Vol. 1, 6th ed., 2008). The previous range
# (-30, 180) deg had this backwards: 180 deg of adduction but only 30 deg of
# abduction.
SHOULDER_ADDUCT_RANGE: tuple[float, float] = (-3.1416, 0.5236)

# Wrist deviation range of motion (radians): same axis/sign convention as
# shoulder adduct (positive = toward the midline). The grip exercises keep
# the hand's orientation consistent with the shaft via the grip weld's own
# frame (#426, exercises/spec_start.py).
WRIST_DEVIATION_RANGE: tuple[float, float] = (-0.3491, 0.5236)


def _three_dof_coord_defs(
    ranges: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> list[dict[str, str | float]]:
    """Coordinate definitions for a flex/adduct/rotate limb root (DRY)."""
    axes = ((_FLEX_AXIS, False), (_ADDUCT_AXIS, True), (_ROTATE_AXIS, True))
    return [
        {
            "suffix": suffix,
            "range_min": lo,
            "range_max": hi,
            "axis": axis,
            "mirror": mirror,
        }
        for suffix, (lo, hi), (axis, mirror) in zip(
            ("flex", "adduct", "rotate"), ranges, axes, strict=True
        )
    ]


def _add_upper_arm(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    shoulder_y: float,
    shoulder_z: float,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral upper-arm segments with 3-DOF shoulder joints."""
    add_bilateral_custom_joint_limb(
        bodyset,
        jointset,
        spec,
        seg_name="upper_arm",
        parent_name="torso",
        parent_offset_y=shoulder_y,
        parent_lateral_z=shoulder_z,
        coord_prefix="shoulder",
        coord_defs=_three_dof_coord_defs(
            ((-1.0472, 3.1416), SHOULDER_ADDUCT_RANGE, (-1.5708, 1.5708))
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
        parent_lateral_z=0,
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
        parent_lateral_z=0,
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
                "range_min": WRIST_DEVIATION_RANGE[0],
                "range_max": WRIST_DEVIATION_RANGE[1],
                "axis": "1 0 0",
                "mirror": True,
            },
        ],
        bodies=bodies,
    )


def add_upper_limbs(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    t_len: float,
    t_rad: float,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral upper-limb segments (arms, forearms, hands)."""
    shoulder_y = t_len * 0.95
    shoulder_z = t_rad * 1.2
    _add_upper_arm(bodyset, jointset, spec, shoulder_y, shoulder_z, bodies)
    _add_forearm(bodyset, jointset, spec, bodies)
    _add_hand(bodyset, jointset, spec, bodies)


def _add_thigh(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    p_len: float,
    hip_z: float,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral thigh segments with 3-DOF hip joints."""
    add_bilateral_custom_joint_limb(
        bodyset,
        jointset,
        spec,
        seg_name="thigh",
        parent_name="pelvis",
        parent_offset_y=-p_len / 2.0,
        parent_lateral_z=hip_z,
        coord_prefix="hip",
        coord_defs=_three_dof_coord_defs(
            ((-0.5236, 2.0944), (-0.7854, 0.5236), (-0.7854, 0.7854))
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
        parent_lateral_z=0,
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
        parent_lateral_z=0,
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
                "mirror": True,
            },
        ],
        bodies=bodies,
    )


def add_lower_limbs(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    p_len: float,
    p_rad: float,
    bodies: dict[str, ET.Element],
) -> None:
    """Add bilateral lower-limb segments (thighs, shanks, feet)."""
    hip_z = p_rad * 0.6
    _add_thigh(bodyset, jointset, spec, p_len, hip_z, bodies)
    _add_shank(bodyset, jointset, spec, bodies)
    _add_foot(bodyset, jointset, spec, bodies)
