"""Real-OpenSim: both hand-to-bar grip constraints hold at the neutral pose.

Issue #394: the left hand is welded to the barbell shaft by a rigid
``WeldJoint`` and the right hand by a ``WeldConstraint`` (OpenSim allows only
one parent joint per body). If the pose's actual hand positions do not match
the shaft's attachment points, the two constraints fight each other.

Measuring only the post-``initSystem`` hand-to-bar distance is not enough to
catch this: OpenSim's ``initSystem()`` silently runs a position assembly for
any model with a position-level constraint, so an infeasible neutral pose
still reports ~0 residual -- after quietly moving a free coordinate (e.g.
``shoulder_r_adduct``) away from its declared default to reconcile the two
hands. That is exactly the "assemble() silently moving the body to an
unrealistic pose" the issue says not to rely on. This test therefore also
asserts that every coordinate's value after ``initSystem()`` matches its
declared default: the pose must already be feasible, not patched up by the
solver.
"""

from __future__ import annotations

import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS

needs_opensim = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="the opensim pip wheel is published for CPython 3.11+ only",
)

TOL_M = 0.005  # 5 mm (issue #394 acceptance criterion)
TOL_DEG = 1.0  # 1 degree (issue #426 orientation acceptance criterion)
# Coordinate drift from initSystem()'s implicit assembly: XML round-trips
# default_value through "%.6f", so ~1e-6 rad of drift is serialization noise,
# not a re-pose. 1e-4 rad (~0.006 deg) is well above that noise floor and
# well below any angle that would move a hand by a visible amount.
COORD_DRIFT_TOL_RAD = 1e-4

GRIP_EXERCISES = ["deadlift", "clean_and_jerk", "snatch", "bench_press"]

# deadlift/clean_and_jerk/snatch keep the hand's orientation consistent with
# the shaft via the grip weld's own frame orientation instead of a wrist
# counter-rotation (#426); bench press is untouched and keeps its existing
# wrist-cancellation behaviour byte-identical, so it is excluded from the
# "wrist stays at 0" and weld-orientation checks below.
WELD_ORIENTATION_EXERCISES = ["deadlift", "clean_and_jerk", "snatch"]


def _frame_translation(root: ET.Element, frame_name: str) -> tuple[float, float, float]:
    """Return the (x, y, z) translation of a named ``PhysicalOffsetFrame``."""
    frame = root.find(f".//PhysicalOffsetFrame[@name='{frame_name}']")
    assert frame is not None, f"frame {frame_name!r} not found in generated model"
    text = frame.findtext("translation")
    assert text is not None
    x, y, z = (float(v) for v in text.split())
    return x, y, z


def _frame_orientation_x_deg(root: ET.Element, frame_name: str) -> float:
    """Return the X component (degrees) of a ``PhysicalOffsetFrame``'s
    body-fixed XYZ Euler ``orientation`` (issue #426: every grip weld
    frame's orientation offset is a pure rotation about the shared
    shoulder-adduct/wrist-deviation axis, confirmed with real-OpenSim FK).
    """
    import math

    frame = root.find(f".//PhysicalOffsetFrame[@name='{frame_name}']")
    assert frame is not None, f"frame {frame_name!r} not found in generated model"
    text = frame.findtext("orientation")
    assert text is not None
    x, _y, _z = (float(v) for v in text.split())
    return math.degrees(x)


def _rotx(angle_rad: float) -> tuple[tuple[float, float, float], ...]:
    """3x3 rotation matrix for a pure rotation about X by *angle_rad*."""
    import math

    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _matmul(
    a: tuple[tuple[float, float, float], ...],
    b: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def _rotation_angle_between_deg(
    a: tuple[tuple[float, float, float], ...],
    b: tuple[tuple[float, float, float], ...],
) -> float:
    """Angle (degrees) between two 3x3 rotation matrices, via trace(A^T B)."""
    a_transpose = tuple(zip(*a, strict=True))
    relative = _matmul(a_transpose, b)  # type: ignore[arg-type]
    trace = relative[0][0] + relative[1][1] + relative[2][2]
    cos_angle = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
    return math.degrees(math.acos(cos_angle))


def _body_rotation_matrix(body, state) -> tuple[tuple[float, float, float], ...]:  # type: ignore[no-untyped-def]
    """Return *body*'s ground-frame rotation matrix at *state*."""
    rot = body.getTransformInGround(state).R()
    return tuple(tuple(rot.get(i, j) for j in range(3)) for i in range(3))


def _weld_orientation_residual_deg(
    body,  # type: ignore[no-untyped-def]
    state,  # type: ignore[no-untyped-def]
    offset_x_deg: float,
    shaft,  # type: ignore[no-untyped-def]
    shaft_offset_x_deg: float,
) -> float:
    """Angular residual (degrees) between a hand-side weld frame and the
    shaft-side weld frame it must coincide with, at the current state.

    Both offsets are a pure rotation about X in their own body's local
    frame (issue #426), so the frame's ground orientation is the body's
    ground rotation composed with that local rotation.
    """
    hand_frame = _matmul(
        _body_rotation_matrix(body, state), _rotx(math.radians(offset_x_deg))
    )
    shaft_frame = _matmul(
        _body_rotation_matrix(shaft, state), _rotx(math.radians(shaft_offset_x_deg))
    )
    return _rotation_angle_between_deg(hand_frame, shaft_frame)


def _residual(opensim, state, body_a, offset_a, body_b, offset_b) -> float:  # type: ignore[no-untyped-def]
    """Euclidean distance (m) between a station on *body_a* and on *body_b*."""
    pt_a = body_a.findStationLocationInGround(state, opensim.Vec3(*offset_a))
    pt_b = body_b.findStationLocationInGround(state, opensim.Vec3(*offset_b))
    return math.sqrt(sum((pt_a.get(i) - pt_b.get(i)) ** 2 for i in range(3)))


def _coordinate_drift(model, state) -> dict[str, float]:  # type: ignore[no-untyped-def]
    """Return ``{coordinate_name: |value - declared_default|}`` after init.

    A model whose neutral pose already satisfies its constraints needs no
    correction, so every entry should be ~0 (XML round-trip noise only).
    """
    coords = model.getCoordinateSet()
    return {
        coords.get(i).getName(): abs(
            coords.get(i).getValue(state) - coords.get(i).getDefaultValue()
        )
        for i in range(coords.getSize())
    }


def _coordinate_range_violations(model) -> dict[str, tuple[float, float, float]]:  # type: ignore[no-untyped-def]
    """Return ``{name: (default, range_min, range_max)}`` for coordinates
    whose own declared default lies outside that coordinate's own declared
    ``<range>`` (issue #424). A default outside its own joint limit is
    infeasible for any limit-aware consumer (IK, optimization, dynamics),
    independent of what OpenSim's own ``initSystem()`` does with it.
    """
    coords = model.getCoordinateSet()
    out = {}
    for i in range(coords.getSize()):
        c = coords.get(i)
        default = c.getDefaultValue()
        lo, hi = c.getRangeMin(), c.getRangeMax()
        if not (lo - 1e-6 <= default <= hi + 1e-6):
            out[c.getName()] = (default, lo, hi)
    return out


def _measure(tmp_path: Path, exercise: str):  # type: ignore[no-untyped-def]
    """Return (left_residual_m, right_residual_m, coordinate_drift) at the
    model's neutral pose, measured right after ``initSystem()``.
    """
    import opensim

    xml_str = EXERCISE_BUILDERS[exercise]()
    root = ET.fromstring(xml_str)
    path = tmp_path / f"{exercise}.osim"
    path.write_text(xml_str, encoding="utf-8")

    model = opensim.Model(str(path))
    state = model.initSystem()
    model.realizePosition(state)

    bodies = model.getBodySet()
    hand_l, hand_r = bodies.get("hand_l"), bodies.get("hand_r")
    shaft = bodies.get("barbell_shaft")

    left_hand_offset = _frame_translation(root, "barbell_to_left_hand_parent")
    left_shaft_offset = _frame_translation(root, "barbell_to_left_hand_child")
    right_hand_offset = _frame_translation(root, "barbell_to_right_hand_frame1")
    right_shaft_offset = _frame_translation(root, "barbell_to_right_hand_frame2")

    left_residual = _residual(
        opensim, state, hand_l, left_hand_offset, shaft, left_shaft_offset
    )
    right_residual = _residual(
        opensim, state, hand_r, right_hand_offset, shaft, right_shaft_offset
    )
    drift = _coordinate_drift(model, state)
    return left_residual, right_residual, drift


@needs_opensim
@pytest.mark.parametrize("exercise", GRIP_EXERCISES)
def test_both_hand_grip_residuals_under_5mm_at_neutral_pose(
    tmp_path: Path, exercise: str
) -> None:
    left_residual, right_residual, _ = _measure(tmp_path, exercise)
    assert left_residual < TOL_M, (
        f"{exercise}: left-hand grip residual {left_residual * 1000:.2f} mm "
        f">= 5 mm at the neutral pose"
    )
    assert right_residual < TOL_M, (
        f"{exercise}: right-hand grip residual {right_residual * 1000:.2f} mm "
        f">= 5 mm at the neutral pose"
    )


@needs_opensim
@pytest.mark.parametrize("exercise", GRIP_EXERCISES)
def test_neutral_pose_needs_no_silent_reassembly(tmp_path: Path, exercise: str) -> None:
    """The declared pose must already satisfy both grips -- #394.

    A model that only passes the residual check because ``initSystem()``
    quietly moved a free coordinate away from its declared default has not
    actually fixed the defect; it has hidden it.
    """
    _, _, drift = _measure(tmp_path, exercise)
    moved = {name: d for name, d in drift.items() if d > COORD_DRIFT_TOL_RAD}
    assert not moved, (
        f"{exercise}: initSystem() silently repositioned {moved} (rad) to "
        f"reconcile the hand-to-bar constraints instead of the declared "
        f"pose already being feasible"
    )


@needs_opensim
@pytest.mark.parametrize("exercise", GRIP_EXERCISES)
def test_initial_pose_within_its_own_joint_limits(
    tmp_path: Path, exercise: str
) -> None:
    """Every barbell exercise's default coordinate values must lie within
    that coordinate's own declared ``<range>`` (issue #424): the shoulder
    adduction range was previously mirrored (180 deg of adduction, 30 deg
    of abduction), which happened to be self-consistent with the clamp in
    ``shoulder_adduct_for_grip`` so it never tripped this check -- but a
    declared default outside its own joint limit is still infeasible for
    any limit-aware consumer.
    """
    import opensim

    xml_str = EXERCISE_BUILDERS[exercise]()
    path = tmp_path / f"{exercise}.osim"
    path.write_text(xml_str, encoding="utf-8")
    model = opensim.Model(str(path))
    model.initSystem()

    violations = _coordinate_range_violations(model)
    assert not violations, f"{exercise}: {violations}"


def test_snatch_achieves_its_documented_0_58m_grip_width() -> None:
    """The snatch now reaches its documented 0.58 m grip exactly (#426).

    #424 found the wrist's own range of motion (not the shoulder's) was the
    real bottleneck: the wrist's exact counter-rotation could not cancel the
    ~45.16 deg of shoulder abduction the full 0.58 m grip needs without
    exceeding its own +30 deg bound, so the achieved width was clamped to
    ~0.4585 m. #426 removes the wrist-cancellation mechanism entirely --
    the grip weld's own frame orientation now keeps the hand consistent
    with the shaft (see ``_weld_orientation_residual_deg`` tests below), so
    ``shoulder_adduct_for_grip`` only needs to clamp to the shoulder's own
    (much larger) range of motion, which the snatch grip does not reach.
    """
    from opensim_models.exercises.constants import _SNATCH_GRIP_HALF_WIDTH

    xml_str = EXERCISE_BUILDERS["snatch"]()
    root = ET.fromstring(xml_str)
    achieved = abs(_frame_translation(root, "barbell_to_left_hand_child")[2])
    assert achieved == pytest.approx(_SNATCH_GRIP_HALF_WIDTH, abs=1e-3)


@pytest.mark.parametrize("exercise", WELD_ORIENTATION_EXERCISES)
def test_wrist_deviation_defaults_are_zero(exercise: str) -> None:
    """The wrist no longer counter-rotates the shoulder's abduction tilt
    (#426): the grip weld's own frame orientation does that job instead, so
    ``wrist_{l,r}_deviation`` stays at its neutral default of 0 for every
    grip exercise that uses the shared ``attach_barbell_to_hands`` helper.
    """
    xml_str = EXERCISE_BUILDERS[exercise]()
    root = ET.fromstring(xml_str)
    jointset = root.find(".//JointSet")
    assert jointset is not None
    for side in ("l", "r"):
        coord = jointset.find(f".//Coordinate[@name='wrist_{side}_deviation']")
        assert coord is not None, f"{exercise}: wrist_{side}_deviation not found"
        default = float(coord.findtext("default_value"))  # type: ignore[arg-type]
        assert default == 0.0, (
            f"{exercise}: wrist_{side}_deviation default is {default}, expected 0.0"
        )


@pytest.mark.parametrize("exercise", WELD_ORIENTATION_EXERCISES)
def test_grip_weld_orientation_mirrors_left_and_right(exercise: str) -> None:
    """The left weld frame's orientation offset and the right weld frame's
    must be exact negatives of each other (#426): both cancel the same
    magnitude of shoulder-adduct tilt, mirrored by the same axis convention
    the shoulder/wrist coordinates themselves use (see
    ``shared/body/limb_builders.py``).
    """
    xml_str = EXERCISE_BUILDERS[exercise]()
    root = ET.fromstring(xml_str)
    left = _frame_orientation_x_deg(root, "barbell_to_left_hand_parent")
    right = _frame_orientation_x_deg(root, "barbell_to_right_hand_frame1")
    assert left == pytest.approx(-right)


@needs_opensim
@pytest.mark.parametrize("exercise", WELD_ORIENTATION_EXERCISES)
def test_grip_weld_orientation_residual_under_1deg_at_neutral_pose(
    tmp_path: Path, exercise: str
) -> None:
    """Both grip welds' orientation, not just position, must be (almost)
    satisfied at the neutral pose (#426): the left weld frame (on hand_l)
    must match the shaft's actual orientation, and so must the right weld
    frame (on hand_r) -- i.e. the shaft stays level and the WeldConstraint's
    own orientation row is satisfied, not just its position rows.
    """
    import opensim

    xml_str = EXERCISE_BUILDERS[exercise]()
    root = ET.fromstring(xml_str)
    path = tmp_path / f"{exercise}.osim"
    path.write_text(xml_str, encoding="utf-8")

    model = opensim.Model(str(path))
    state = model.initSystem()
    model.realizePosition(state)

    bodies = model.getBodySet()
    hand_l, hand_r = bodies.get("hand_l"), bodies.get("hand_r")
    shaft = bodies.get("barbell_shaft")

    left_hand_x = _frame_orientation_x_deg(root, "barbell_to_left_hand_parent")
    left_shaft_x = _frame_orientation_x_deg(root, "barbell_to_left_hand_child")
    right_hand_x = _frame_orientation_x_deg(root, "barbell_to_right_hand_frame1")
    right_shaft_x = _frame_orientation_x_deg(root, "barbell_to_right_hand_frame2")

    left_residual = _weld_orientation_residual_deg(
        hand_l, state, left_hand_x, shaft, left_shaft_x
    )
    right_residual = _weld_orientation_residual_deg(
        hand_r, state, right_hand_x, shaft, right_shaft_x
    )
    assert left_residual < TOL_DEG, (
        f"{exercise}: left-hand weld orientation residual "
        f"{left_residual:.3f} deg >= {TOL_DEG:.0f} deg at the neutral pose"
    )
    assert right_residual < TOL_DEG, (
        f"{exercise}: right-hand (WeldConstraint) orientation residual "
        f"{right_residual:.3f} deg >= {TOL_DEG:.0f} deg at the neutral pose"
    )


def test_bench_press_grip_mechanism_is_unchanged() -> None:
    """Bench press is explicitly out of scope for #426 and must stay
    byte-identical: it keeps the old wrist-cancellation mechanism, so its
    grip weld frames carry no orientation offset and its wrist deviation
    default is the (nonzero) exact counter-rotation, not 0.
    """
    xml_str = EXERCISE_BUILDERS["bench_press"]()
    root = ET.fromstring(xml_str)
    assert _frame_orientation_x_deg(root, "barbell_to_left_hand_parent") == 0.0
    assert _frame_orientation_x_deg(root, "barbell_to_right_hand_frame1") == 0.0

    jointset = root.find(".//JointSet")
    assert jointset is not None
    coord = jointset.find(".//Coordinate[@name='wrist_l_deviation']")
    assert coord is not None
    default = float(coord.findtext("default_value"))  # type: ignore[arg-type]
    assert default != 0.0
