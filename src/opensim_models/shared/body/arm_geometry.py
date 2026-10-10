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

Keeping hand *orientation* consistent with the shaft is not merely
cosmetic (#424): the left hand is welded to the barbell shaft by a rigid,
zero-DOF ``WeldJoint`` (the shaft's orientation *is* the left hand's
orientation), and the right hand is tied to that same shaft by a
``WeldConstraint``, which constrains orientation as well as position. A
mismatch between the two hands' orientations is not just cosmetic either:
OpenSim's ``initSystem()`` assembly would silently redistribute it across
whichever coordinates are free to move, moving them away from their
declared defaults.

#424 kept the two hands' orientations consistent (and so avoided that
mismatch) with an equal, opposite wrist deviation on the same mirrored
axis (``wrist_deviation = -shoulder_adduct``), confirmed with real-OpenSim
forward kinematics to give zero coordinate drift and zero grip residual
at any angle -- but only up to the wrist's own declared range (+30/-20
deg), which the snatch's documented 0.58 m grip (~45.16 deg of abduction)
exceeds. #426 removes that dependency on the wrist entirely: the grip
weld's own frame now carries the exact inverse rotation of each hand's
tilt (``exercises.base.attach_barbell_to_hands``'s ``hand_tilt``
parameter), confirmed with real-OpenSim forward kinematics (isolated from
every other pose coordinate): ``hand_l = RotX(-shoulder_l_adduct)``,
``hand_r = RotX(+shoulder_r_adduct)``, both about the shoulder/wrist's
shared mirrored axis. The wrist stays at its neutral default of 0 for
every grip exercise, so ``shoulder_adduct_for_grip`` only needs to clamp
its angle to the shoulder's own range of motion.
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
    the hand's lateral offset at *grip_offset* at the neutral pose. It is
    clamped to the shoulder's own range of motion only (#426; see module
    docstring for why the wrist's range no longer bounds it).
    ``feasible_grip_offset`` is the lateral offset actually reached at that
    clamped angle: equal to *grip_offset* unless the request exceeds the
    shoulder's range, in which case it is the widest grip the pose can
    reach.

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
