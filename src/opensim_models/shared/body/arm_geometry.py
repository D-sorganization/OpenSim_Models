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
correction is needed to satisfy the two hand-to-bar grip *position*
constraints.

The wrist counter-rotation is not merely cosmetic, though (#424): the left
hand is welded to the barbell shaft by a rigid, zero-DOF ``WeldJoint`` (the
shaft's orientation *is* the left hand's orientation), and the right hand
is tied to that same shaft by a ``WeldConstraint``, which constrains
orientation as well as position. Confirmed with real-OpenSim forward
kinematics: the exact cancellation ``wrist_deviation = -shoulder_adduct``
gives zero coordinate drift and zero grip residual at any angle, but
clamping the wrist's value independently (leaving ``shoulder_adduct``
at an angle the wrist cannot fully cancel) does not just leave the hand
visually tilted -- it leaves the two hands' orientations mismatched, so
OpenSim's ``initSystem()`` assembly silently redistributes the mismatch
across *both* wrists, moving each one away from its declared default.
``shoulder_adduct_for_grip`` therefore clamps its angle to the
intersection of the shoulder's own range and the range the wrist can
exactly cancel, not the shoulder's range alone.
"""

from __future__ import annotations

import math

from opensim_models.shared.body._segment_data import BodyModelSpec, _seg
from opensim_models.shared.body.body_model import (
    SHOULDER_ADDUCT_RANGE,
    WRIST_DEVIATION_RANGE,
)
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
    the hand's lateral offset at *grip_offset* at the neutral pose. It is
    clamped to the intersection of the shoulder's own range of motion and
    the range the wrist's exact counter-rotation (``-shoulder_adduct``,
    see module docstring) can reach without exceeding the wrist's own
    declared range (#424) -- exceeding it would force OpenSim's
    ``initSystem()`` to silently redistribute the mismatch across both
    wrists at assembly time. ``feasible_grip_offset`` is the lateral
    offset actually reached at that clamped angle: equal to *grip_offset*
    unless the request exceeds this combined range, in which case it is
    the widest grip the pose can reach without assembly-time drift.

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
    wrist_lo, wrist_hi = WRIST_DEVIATION_RANGE
    lo, hi = max(lo, -wrist_hi), min(hi, -wrist_lo)
    theta = max(lo, min(hi, theta))
    feasible_grip_offset = shoulder_z - arm_length * math.sin(theta)
    return theta, feasible_grip_offset
