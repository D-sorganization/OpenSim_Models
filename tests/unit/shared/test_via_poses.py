"""Engine-free tests of the spec via-pose conversion to OpenSim terms."""

from __future__ import annotations

import math

import numpy as np
import pytest

from opensim_models.shared.parity import via_poses
from opensim_models.shared.parity._canonical import conformance, spec

STD = conformance.load_standard()


def _rx(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _ry(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rz(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


@pytest.mark.parametrize("angles", [(0.1, -0.4, 1.2), (-1.0, 0.3, -2.5), (0, 0, 0)])
def test_body_xyz_angles_invert_rx_ry_rz(angles: tuple[float, float, float]) -> None:
    rot = _rx(angles[0]) @ _ry(angles[1]) @ _rz(angles[2])
    assert via_poses.body_xyz_angles(rot) == pytest.approx(angles)


def test_body_xyz_angles_reject_a_non_rotation() -> None:
    with pytest.raises(ValueError, match="rotation"):
        via_poses.body_xyz_angles(np.eye(3) * 2.0)


def test_canonical_up_is_opensim_y_and_left_is_minus_z() -> None:
    assert via_poses.to_engine((0, 0, 1)) == pytest.approx((0, 1, 0))
    assert via_poses.to_engine((0, 1, 0)) == pytest.approx((0, 0, -1))


def test_deadlift_root_pitch_is_an_opensim_z_rotation() -> None:
    """Positive canonical pitch leans the trunk forward: OpenSim Rz(-pitch)."""
    root = spec.exercise_spec(STD, "deadlift")["via_poses"]["start"]["root"]
    got = via_poses.root_coordinates("deadlift", "start", 1.75)
    pitch = root["orientation_rpy_rad"][1]
    assert (got["pelvis_rx"], got["pelvis_ry"]) == pytest.approx((0.0, 0.0))
    assert got["pelvis_rz"] == pytest.approx(-pitch)
    x, y, z = root["position_m"]
    assert (got["pelvis_tx"], got["pelvis_ty"], got["pelvis_tz"]) == pytest.approx(
        (x, z, -y)
    )


def test_positions_scale_with_height_and_angles_do_not() -> None:
    short = via_poses.root_coordinates("squat", "start", 1.75)
    tall = via_poses.root_coordinates("squat", "start", 2.1)
    assert tall["pelvis_ty"] == pytest.approx(short["pelvis_ty"] * 2.1 / 1.75)
    assert tall["pelvis_rz"] == pytest.approx(short["pelvis_rz"])


def test_coordinates_cover_every_canonical_coordinate_under_opensim_names() -> None:
    pose = via_poses.coordinates("snatch", "start")
    assert len(pose) == len(conformance.expected_coordinates(STD))
    assert "wrist_l_deviation" in pose
    assert "ankle_r_inversion" in pose


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda: via_poses.coordinates("squat", "midway"), "via-pose"),
        (lambda: via_poses.height_scale(0.0), "height"),
        (lambda: via_poses.height_scale(float("nan")), "height"),
        (lambda: via_poses.segment_frame("squat", "start", "tail", 1.75), "segment"),
    ],
)
def test_preconditions_raise_value_error(call, match: str) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=match):
        call()
