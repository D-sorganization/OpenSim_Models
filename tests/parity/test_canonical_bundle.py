"""Engine-free tests for the vendored ``kinematics`` and ``topology`` modules.

The 3.10 CI lane has no opensim wheel, so these exercise the pure-Python
reference kinematics directly. They must never import ``opensim``.
Refs D-sorganization/Repository_Management#2011.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

from opensim_models.shared.parity._canonical import conformance, kinematics, topology

STD = conformance.load_standard()
TOL = STD["tolerances"]["cross_engine_position_abs_m"]
IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _rot_z(angle: float) -> list[list[float]]:
    c, s = math.cos(angle), math.sin(angle)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _std_with(**kin: Any) -> dict[str, Any]:
    std = copy.deepcopy(STD)
    std["kinematics"].update(kin)
    return std


# --- kinematics -------------------------------------------------------------


def test_expected_axes_expand_sides_and_mirror_left() -> None:
    axes = kinematics.expected_axes(STD)
    assert axes["lumbar_flex"] == (0.0, 1.0, 0.0)
    right, left = axes["shoulder_r_adduct"], axes["shoulder_l_adduct"]
    assert left == tuple(-v + 0.0 for v in right)
    assert axes["shoulder_l_flex"] == axes["shoulder_r_flex"]  # mirror=false
    assert all(math.isclose(math.hypot(*a), 1.0) for a in axes.values())


def test_axis_probes_name_the_measured_segment() -> None:
    probes = kinematics.axis_probes(STD)
    assert probes["lumbar_flex"] == "torso"
    assert probes["elbow_l_flex"] == "forearm_l"
    assert set(probes) == set(kinematics.expected_axes(STD))


def test_probe_angle_is_standard_probe_in_radians() -> None:
    deg = STD["kinematics"]["probe_angle_deg"]
    assert kinematics.probe_angle_rad(STD) == pytest.approx(math.radians(deg))


def test_segment_axis_recovers_rotation_axis() -> None:
    axis = kinematics.segment_axis(IDENTITY, IDENTITY, IDENTITY, _rot_z(0.2))
    assert axis == pytest.approx((0.0, 0.0, 1.0))


def test_segment_axis_cancels_pelvis_motion() -> None:
    pelvis = _rot_z(0.7)
    seg_after = _rot_z(0.7 + 0.2)  # pelvis and segment both turned
    axis = kinematics.segment_axis(IDENTITY, IDENTITY, pelvis, seg_after)
    assert axis == pytest.approx((0.0, 0.0, 1.0))


def test_segment_axis_rejects_no_rotation() -> None:
    with pytest.raises(ValueError, match="did not rotate"):
        kinematics.segment_axis(IDENTITY, IDENTITY, IDENTITY, IDENTITY)


def _axes_fp(**overrides: Any) -> dict[str, Any]:
    axes: dict[str, Any] = {
        n: list(a) for n, a in kinematics.expected_axes(STD).items()
    }
    axes.update(overrides)
    return {"coordinate_axes": axes}


def test_check_axes_not_checked_when_absent() -> None:
    assert kinematics.check_axes({}, STD) == []


def test_check_axes_clean_for_standard_axes() -> None:
    assert kinematics.check_axes(_axes_fp(), STD) == []


def test_check_axes_flags_flipped_axis() -> None:
    findings = kinematics.check_axes(_axes_fp(lumbar_flex=[0, -1, 0]), STD)
    assert [f[0] for f in findings] == ["axis.lumbar_flex"]
    assert "off by 180.0" in findings[0][3]


def test_check_axes_flags_missing_and_zero_axes() -> None:
    fp = _axes_fp(neck_flex=[0, 0, 0])
    del fp["coordinate_axes"]["lumbar_rotate"]
    keys = {f[0] for f in kinematics.check_axes(fp, STD)}
    assert keys == {"axis.neck_flex", "axis.lumbar_rotate.missing"}


def test_check_sides_accepts_left_plus_y_right_minus_y() -> None:
    origins = {"pelvis": [0, 0, 0], "hip_l": [0, 0.1, 0], "hip_r": [0, -0.1, 0]}
    fp = {"segment_origins_neutral_m": origins}
    assert kinematics.check_sides(fp, STD) == []


def test_check_sides_flags_swapped_sides_and_skips_midline() -> None:
    origins = {"torso": [0, 0.0, 0.5], "thigh_l": [0, -0.1, 0], "thigh_r": [0, 0.1, 0]}
    findings = kinematics.check_sides({"segment_origins_neutral_m": origins}, STD)
    assert [f[0] for f in findings] == ["side.thigh_l", "side.thigh_r"]
    assert findings[0][1] == "+Y (left)"
    assert findings[1][1] == "-Y (right)"


# --- topology ---------------------------------------------------------------


def test_joints_expand_sides_with_mirrored_lateral_offset() -> None:
    table = {seg: (parent, off) for seg, parent, off in topology.joints(STD)}
    assert table["torso"][0] == "pelvis"
    parent_l, off_l = table["upper_arm_l"]
    parent_r, off_r = table["upper_arm_r"]
    assert (parent_l, parent_r) == ("torso", "torso")
    assert off_l[1] > 0.0 and off_r[1] == -off_l[1]
    assert off_l[0] == off_r[0] and off_l[2] == off_r[2]


def test_every_joint_parent_precedes_its_child() -> None:
    seen = {"pelvis"}
    for seg, parent, _ in topology.joints(STD):
        assert parent in seen
        seen.add(seg)
    assert seen == set(conformance.expected_segments(STD))


def test_standard_poses_are_radians_of_known_coordinates() -> None:
    poses = topology.standard_poses(STD)
    assert set(poses) == set(STD["kinematics"]["test_poses"])
    assert poses["flexion"]["hip_l_flex"] == pytest.approx(math.radians(60))


def test_standard_poses_reject_unknown_coordinate() -> None:
    bad = _std_with(test_poses={"p": {"not_a_coordinate": 10}})
    with pytest.raises(ValueError, match="unknown coordinate"):
        topology.standard_poses(bad)


def test_standard_poses_reject_two_angles_on_one_segment() -> None:
    bad = _std_with(test_poses={"p": {"shoulder_r_flex": 10, "shoulder_r_adduct": 5}})
    with pytest.raises(ValueError, match="more than one angle"):
        topology.standard_poses(bad)


def test_neutral_origins_cover_pelvis_and_all_segments() -> None:
    origins = topology.reference_origins(STD, {})
    assert origins["pelvis"] == (0.0, 0.0, 0.0)
    assert set(origins) == set(conformance.expected_segments(STD))
    assert origins["torso"][2] > 0.0  # torso above pelvis (canonical Z up)
    assert origins["upper_arm_l"][1] > 0.0 > origins["upper_arm_r"][1]


def test_rotating_a_joint_moves_children_not_itself_and_keeps_lengths() -> None:
    neutral = topology.reference_origins(STD, {})
    posed = topology.reference_origins(STD, {"lumbar_flex": math.pi / 2})
    assert posed["torso"] == pytest.approx(neutral["torso"])
    assert posed["head"] != pytest.approx(neutral["head"])
    assert math.dist(posed["head"], posed["torso"]) == pytest.approx(
        math.dist(neutral["head"], neutral["torso"])
    )


def test_reference_origins_reject_unknown_coordinate() -> None:
    with pytest.raises(ValueError, match="unknown coordinate"):
        topology.reference_origins(STD, {"bogus": 0.1})


def _reference_fp() -> dict[str, Any]:
    def listed(origins: dict[str, Any]) -> dict[str, list[float]]:
        return {s: list(v) for s, v in origins.items()}

    return {
        "segment_origins_neutral_m": listed(topology.reference_origins(STD, {})),
        "segment_origins_test_poses_m": {
            pose: listed(topology.reference_origins(STD, q))
            for pose, q in topology.standard_poses(STD).items()
        },
    }


def test_check_origins_skipped_without_test_poses() -> None:
    assert topology.check_origins({"segment_origins_neutral_m": {}}, STD) == []


def test_check_origins_clean_for_reference_fingerprint() -> None:
    assert topology.check_origins(_reference_fp(), STD) == []


def test_check_origins_flags_displaced_segment_in_one_pose() -> None:
    fp = _reference_fp()
    fp["segment_origins_test_poses_m"]["flexion"]["head"][0] += 10 * TOL
    findings = topology.check_origins(fp, STD)
    assert [f[0] for f in findings] == ["pose.flexion.head"]
    assert "head off by" in findings[0][3]


def test_check_origins_flags_missing_segment_and_pose() -> None:
    fp = _reference_fp()
    del fp["segment_origins_neutral_m"]["head"]
    del fp["segment_origins_test_poses_m"]["axial"]
    keys = {f[0] for f in topology.check_origins(fp, STD)}
    assert keys == {"origin.head.missing", "pose.axial.missing"}
