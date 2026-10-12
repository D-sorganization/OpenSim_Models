"""Spec via-poses expressed in OpenSim terms (engine-free, no opensim import).

UpstreamDrift#11743 (LIFT-3): the generators place every barbell lift at its
standard ``start`` via-pose. The standard states a via-pose in the canonical
``pose_frame`` (X forward, Y left, Z up, origin on the floor at mid-foot) at
the reference height; this module converts it to OpenSim's Y-up world and
coordinate names, using the vendored reference forward kinematics
(``_canonical/topology.py``) wherever a segment frame is needed. The pack's
segment geometry equals that reference (``test_engine_conformance.py``).

Positions scale linearly with the lifter's height; angles do not
(``pose_frame``).

Design by Contract:
    - Preconditions: the exercise and pose exist in the standard and the
      height is positive and finite; violations raise ValueError.
    - Postconditions: rotations returned are orthonormal; Euler triples are
      OpenSim body-fixed X-Y-Z angles (FreeJoint coordinates and
      PhysicalOffsetFrame ``orientation``).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray

from opensim_models.shared.parity._canonical import conformance, spec, topology
from opensim_models.shared.parity.aliases import engine_name
from opensim_models.shared.parity.standard import STANDARD, STANDARD_HEIGHT

Vec3 = tuple[float, float, float]
Mat = NDArray[np.float64]

# Canonical = M @ OpenSim, for world vectors and segment-local vectors alike.
_TO_CANONICAL: Mat = np.array(STANDARD["frame"]["to_canonical"]["y_up"], dtype=float)
ROOT_COORDINATES: tuple[str, ...] = tuple(
    f"pelvis_{axis}" for axis in ("rx", "ry", "rz", "tx", "ty", "tz")
)


def _pose(exercise: str, pose: str) -> dict[str, Any]:
    poses = spec.exercise_spec(STANDARD, exercise).get("via_poses", {})
    if pose not in poses:
        raise ValueError(f"{exercise!r} has no via-pose {pose!r}; has {sorted(poses)}")
    return dict(poses[pose])


def height_scale(height_m: float) -> float:
    """Factor from the standard's reference height to *height_m*."""
    if not (math.isfinite(height_m) and height_m > 0):
        raise ValueError(f"height must be positive and finite, got {height_m!r}")
    return height_m / STANDARD_HEIGHT


def to_engine(vec: Any) -> Mat:
    """Canonical vector -> OpenSim vector (world or segment-local)."""
    return _TO_CANONICAL.T @ np.asarray(vec, dtype=float)


def rotation_to_engine(rot: Any) -> Mat:
    """Canonical rotation (canonical axes both sides) -> OpenSim rotation."""
    return _TO_CANONICAL.T @ np.asarray(rot, dtype=float) @ _TO_CANONICAL


def body_xyz_angles(rot: Any) -> Vec3:
    """Body-fixed X-Y-Z Euler angles ``(a, b, c)`` with ``R = Rx(a) Ry(b) Rz(c)``.

    Raises:
        ValueError: *rot* is not a 3x3 rotation matrix.
    """
    r = np.asarray(rot, dtype=float)
    if r.shape != (3, 3) or not np.allclose(r @ r.T, np.eye(3), atol=1e-9):
        raise ValueError("expected a 3x3 orthonormal rotation matrix")
    b = math.asin(max(-1.0, min(1.0, float(r[0, 2]))))
    a = math.atan2(-float(r[1, 2]), float(r[2, 2]))
    c = math.atan2(-float(r[0, 1]), float(r[0, 0]))
    return a, b, c


def coordinates(exercise: str, pose: str) -> dict[str, float]:
    """Joint angles (rad) of a via-pose under OpenSim coordinate names.

    Every canonical coordinate is present, both sides; those the spec does not
    list are 0 (``pose_frame``).
    """
    _pose(exercise, pose)
    canonical = dict.fromkeys(conformance.expected_coordinates(STANDARD), 0.0)
    canonical.update(spec.pose_coordinates(STANDARD, exercise, pose))
    return {engine_name(name): value for name, value in canonical.items()}


def root_position(exercise: str, pose: str, height_m: float) -> Mat:
    """Pelvis origin of a via-pose in the OpenSim world (metres)."""
    root = _pose(exercise, pose)["root"]
    return to_engine(root["position_m"]) * height_scale(height_m)


def root_rotation(exercise: str, pose: str) -> Mat:
    """Pelvis rotation of a via-pose in the OpenSim world."""
    rpy = _pose(exercise, pose)["root"]["orientation_rpy_rad"]
    return rotation_to_engine(topology.rpy_matrix(rpy))


def root_coordinates(exercise: str, pose: str, height_m: float) -> dict[str, float]:
    """The pelvis FreeJoint coordinates (``pelvis_rx`` .. ``pelvis_tz``)."""
    angles = body_xyz_angles(root_rotation(exercise, pose))
    position = root_position(exercise, pose, height_m)
    values = (*angles, *(float(v) for v in position))
    return dict(zip(ROOT_COORDINATES, values, strict=True))


def bar_position(exercise: str, pose: str, height_m: float) -> Mat:
    """Bar centre of a via-pose in the OpenSim world (metres)."""
    bar = _pose(exercise, pose)["bar_position_m"]
    return to_engine(bar) * height_scale(height_m)


def segment_frame(
    exercise: str, pose: str, segment: str, height_m: float
) -> tuple[Mat, Mat]:
    """OpenSim world ``(origin, rotation)`` of a human segment at a via-pose."""
    root = _pose(exercise, pose)["root"]
    frames = topology.world_frames(
        STANDARD,
        spec.pose_coordinates(STANDARD, exercise, pose),
        root["position_m"],
        root["orientation_rpy_rad"],
    )
    if segment not in frames:
        raise ValueError(f"unknown segment {segment!r}")
    origin, rot = frames[segment]
    return to_engine(origin) * height_scale(height_m), rotation_to_engine(rot)


def palm_offset(height_m: float) -> Mat:
    """Palm centre in the hand segment frame (OpenSim axes, metres)."""
    factor, term = STANDARD["grip_point"]["origin"]["z"]
    local = (0.0, 0.0, float(factor) * topology.dimension(STANDARD, term))
    return to_engine(local) * height_scale(height_m)


def grip_half_width(exercise: str, height_m: float) -> float:
    """Shaft centre to palm centre along the bar (metres)."""
    width = spec.exercise_spec(STANDARD, exercise)["grip"]["width_m"]
    return float(width) / 2.0 * height_scale(height_m)


def plates_per_side_kg(exercise: str) -> float:
    """Plate mass per sleeve of the exercise's spec load (kg)."""
    return float(spec.exercise_spec(STANDARD, exercise)["load"]["plates_per_side_kg"])


def point_in_segment(
    exercise: str, pose: str, segment: str, point: Any, height_m: float
) -> tuple[Mat, Vec3]:
    """A world point and the world axes, seen from *segment* at a via-pose.

    Returns ``(location, orientation)``: *point* (OpenSim world, metres) in the
    segment frame, and the body-fixed X-Y-Z angles of the world axes in that
    frame -- the weld frame that holds a world-aligned body there.
    """
    origin, rot = segment_frame(exercise, pose, segment, height_m)
    location = rot.T @ (np.asarray(point, dtype=float) - origin)
    return location, body_xyz_angles(rot.T)
