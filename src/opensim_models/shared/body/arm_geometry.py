"""Shoulder-abduction geometry for a symmetric barbell grip (#394).

Forward kinematics of the shoulder -> elbow -> hand chain (see
``body_model.py``) reduces to a single equation for the hand's lateral
offset from the torso midline, because:

- the shoulder's flexion axis (Z) and the pelvis-supine pre-rotation that
  bench press applies are both rotations about Z, so neither changes the
  hand's lateral (Z) coordinate;
- the elbow and wrist flexion axes are 0 for every barbell exercise, so they
  contribute no rotation;
- the shoulder's long-axis rotation is 0 for every barbell exercise.

What remains is the shoulder's adduction (about X), applied once at the
shoulder. An equal, opposite wrist deviation on the same axis keeps the hand
level without moving it -- the hand body's own frame origin sits exactly at
the wrist joint, so the wrist's rotation changes the hand's orientation only,
never its position:

    z_hand = shoulder_z - (upper_arm_length + forearm_length) * sin(adduct)

Solving for *adduct* given a target grip half-width keeps both hands
symmetric about the shaft centre by construction, so no assembly-time
correction is needed to satisfy the two hand-to-bar grip constraints.
"""

from __future__ import annotations

import math

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.body.body_model import SHOULDER_ADDUCT_RANGE
from opensim_models.shared.contracts.preconditions import require_finite

# Lateral offset of the shoulder joint from the torso midline, as a multiple
# of the torso radius. Must match _add_upper_limbs' shoulder_z in
# body_model.py (single source of truth for the body geometry itself; this
# module only reuses the resulting segment lengths).
_SHOULDER_LATERAL_FACTOR = 1.2


def _shoulder_lateral_offset(spec: BodyModelSpec) -> float:
    """Lateral distance from the torso midline to the shoulder joint."""
    _, _, torso_radius = _seg(spec, "torso")
    return torso_radius * _SHOULDER_LATERAL_FACTOR


def _arm_length(spec: BodyModelSpec) -> float:
    """Combined upper-arm + forearm length (shoulder to wrist)."""
    _, upper_arm_length, _ = _seg(spec, "upper_arm")
    _, forearm_length, _ = _seg(spec, "forearm")
    return upper_arm_length + forearm_length


def shoulder_adduct_for_grip(
    spec: BodyModelSpec, grip_offset: float
) -> tuple[float, float]:
    """Return ``(shoulder_adduct, feasible_grip_offset)`` for a symmetric grip.

    ``shoulder_adduct`` is the shoulder-adduction angle (radians) that puts
    the hand's lateral offset at *grip_offset* at the neutral pose, clamped
    to the shoulder's valid range of motion. ``feasible_grip_offset`` is the
    lateral offset actually reached at that clamped angle: equal to
    *grip_offset* unless the request exceeds the shoulder's range of motion,
    in which case it is the widest grip the pose can reach.

    Callers must attach the barbell at ``feasible_grip_offset``, not the
    raw request, or the two hand-to-bar constraints fight each other at the
    neutral pose (#394).

    Precondition: grip_offset is finite.
    """
    require_finite(grip_offset, "grip_offset")
    shoulder_z = _shoulder_lateral_offset(spec)
    arm_length = _arm_length(spec)
    sin_theta = (shoulder_z - grip_offset) / arm_length
    sin_theta = max(-1.0, min(1.0, sin_theta))
    theta = math.asin(sin_theta)
    lo, hi = SHOULDER_ADDUCT_RANGE
    theta = max(lo, min(hi, theta))
    feasible_grip_offset = shoulder_z - arm_length * math.sin(theta)
    return theta, feasible_grip_offset
