"""Every barbell lift's generated model starts at its spec ``start`` via-pose.

UpstreamDrift#11743 (LIFT-3): the joint coordinates, the pelvis root, the bar,
the feet and the grip of each generated model equal the vendored standard's
``start`` via-pose (``pose_frame``: canonical X forward, Y left, Z up, origin on
the floor at mid-foot). The masses equal the reference body and the spec load,
and the combined body + bar centre of mass sits over mid-foot.

The XML checks run anywhere; the forward-kinematics checks need real OpenSim
(the pip wheel is CPython 3.11+).
"""

from __future__ import annotations

import functools
import logging
import math
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.exercises.base import ExerciseConfig
from opensim_models.exercises.deadlift.deadlift_model import DeadliftModelBuilder
from opensim_models.shared.body.foot_seating import (
    contact_heights,
    equilibrium_depth,
    supported_weight,
)
from opensim_models.shared.parity._canonical import conformance, spec, topology
from opensim_models.shared.parity.aliases import engine_name

pytestmark = pytest.mark.requires_opensim

logger = logging.getLogger(__name__)

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None,
    reason="opensim is not installed in this Python environment",
)

STD = conformance.load_standard()
TOL = STD["tolerances"]
LIFTS = ("squat", "deadlift", "bench_press", "snatch", "clean_and_jerk")
PULLS = ("deadlift", "snatch", "clean_and_jerk")
# The bench lifter lies on the bench: the bench, not the feet, carries the CoM.
STANDING = ("squat", "deadlift", "snatch", "clean_and_jerk")
POSITION_TOL_M = 0.001  # spec placement is exact up to the XML's 1e-6 rounding
GRIP_TOL_M = 0.005  # hand-bar closure (Repository_Management#2060 condition 1)
FOOT_TOL_M = 0.005
G = float(STD["frame"]["gravity_mps2"])


def _start(exercise: str) -> dict[str, Any]:
    return spec.exercise_spec(STD, exercise)["via_poses"]["start"]


def _human_coordinates(exercise: str) -> dict[str, float]:
    """Spec start coordinates under OpenSim names, both sides, unlisted 0."""
    out = dict.fromkeys(conformance.expected_coordinates(STD), 0.0)
    out.update(spec.pose_coordinates(STD, exercise, "start"))
    return {engine_name(name): value for name, value in out.items()}


@functools.cache
def _xml(exercise: str) -> ET.Element:
    return ET.fromstring(EXERCISE_BUILDERS[exercise]())


def _coordinate(root: ET.Element, name: str) -> ET.Element:
    coord = root.find(f".//Coordinate[@name='{name}']")
    assert coord is not None, name
    return coord


def _masses(root: ET.Element) -> dict[str, float]:
    return {
        str(b.get("name")): float(b.findtext("mass") or "nan")
        for b in root.iter("Body")
    }


# --- XML (engine-free) ---------------------------------------------------------


@pytest.mark.parametrize("exercise", LIFTS)
def test_start_coordinates_equal_the_spec_start_pose(exercise: str) -> None:
    root = _xml(exercise)
    for name, want in _human_coordinates(exercise).items():
        got = float(_coordinate(root, name).findtext("default_value") or "nan")
        assert got == pytest.approx(want, abs=TOL["limit_abs_rad"]), name


@pytest.mark.parametrize("exercise", LIFTS)
def test_start_coordinates_lie_within_the_model_joint_limits(exercise: str) -> None:
    root = _xml(exercise)
    for name in _human_coordinates(exercise):
        coord = _coordinate(root, name)
        lo, hi = (float(v) for v in (coord.findtext("range") or "").split())
        value = float(coord.findtext("default_value") or "nan")
        assert lo <= value <= hi, f"{name}={value} outside [{lo}, {hi}]"


@pytest.mark.parametrize("exercise", LIFTS)
def test_human_masses_equal_the_reference_body(exercise: str) -> None:
    masses = _masses(_xml(exercise))
    want = conformance.expected_segments(STD)
    for segment, mass in want.items():
        assert masses[segment] == pytest.approx(mass, rel=TOL["mass_rel"]), segment
    human = sum(masses[s] for s in want)
    body_mass = STD["anthropometrics"]["body_mass_kg"]
    assert human == pytest.approx(body_mass, rel=TOL["mass_rel"])


@pytest.mark.parametrize("exercise", LIFTS)
def test_barbell_mass_equals_the_spec_load(exercise: str) -> None:
    masses = _masses(_xml(exercise))
    load = spec.exercise_spec(STD, exercise)["load"]
    want = STD["barbell"]["mens"]["bar_mass_kg"] + 2 * load["plates_per_side_kg"]
    got = sum(m for name, m in masses.items() if name.startswith("barbell"))
    assert got == pytest.approx(want, rel=TOL["mass_rel"])


def test_a_grip_other_than_the_spec_grip_is_rejected() -> None:
    """The start pose is solved for the spec grip; another width cannot close."""
    builder = DeadliftModelBuilder(ExerciseConfig(grip_offset=0.40))
    with pytest.raises(ValueError, match="grip"):
        builder.build()


# --- Real-OpenSim forward kinematics -----------------------------------------


@functools.cache
def _engine(exercise: str, height: float | None = None) -> tuple[Any, Any]:
    """(model, state) of the generated model at its defaults, after initSystem."""
    import opensim

    opensim.Logger.setLevelString("Error")
    builder = EXERCISE_BUILDERS[exercise]
    xml = builder() if height is None else builder(height=height)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{exercise}.osim"
        path.write_text(xml, encoding="utf-8")
        model = opensim.Model(str(path))
    state = model.initSystem()
    model.realizePosition(state)
    return model, state


def _canonical(vec: Any) -> tuple[float, float, float]:
    return conformance.to_canonical(STD, "opensim", [vec.get(i) for i in range(3)])


def _station(exercise: str, body: str, local: tuple[float, ...] = (0, 0, 0)):  # type: ignore[no-untyped-def]
    import opensim

    model, state = _engine(exercise)
    point = (
        model.getBodySet()
        .get(body)
        .findStationLocationInGround(state, opensim.Vec3(*local))
    )
    return _canonical(point)


def _rotation(exercise: str, body: str) -> list[list[float]]:
    """Body rotation in the canonical world frame (canonical body axes)."""
    model, state = _engine(exercise)
    rot = model.getBodySet().get(body).getTransformInGround(state).R()
    m = STD["frame"]["to_canonical"]["y_up"]
    raw = [[rot.get(i, j) for j in range(3)] for i in range(3)]
    # R_canonical = M R_engine M^T
    mr = [
        [sum(m[i][k] * raw[k][j] for k in range(3)) for j in range(3)] for i in range(3)
    ]
    return [
        [sum(mr[i][k] * m[j][k] for k in range(3)) for j in range(3)] for i in range(3)
    ]


def _max_abs_diff(a: list[list[float]], b: Any) -> float:
    return max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3))


def _palm(exercise: str, side: str) -> tuple[float, float, float]:
    factor, term = STD["grip_point"]["origin"]["z"]
    # Canonical segment z is OpenSim segment y (Y-up frames).
    return _station(
        exercise, f"hand_{side}", (0, factor * topology.dimension(STD, term), 0)
    )


@needs_opensim
@pytest.mark.parametrize("exercise", LIFTS)
def test_pelvis_root_equals_the_spec_root(exercise: str) -> None:
    root = _start(exercise)["root"]
    pelvis = _station(exercise, "pelvis")
    assert math.dist(pelvis, root["position_m"]) <= POSITION_TOL_M, pelvis
    want = topology.rpy_matrix(root["orientation_rpy_rad"])
    assert _max_abs_diff(_rotation(exercise, "pelvis"), want) <= TOL["limit_abs_rad"]


@needs_opensim
@pytest.mark.parametrize("exercise", LIFTS)
def test_bar_centre_is_at_the_spec_bar_position(exercise: str) -> None:
    bar = _station(exercise, "barbell_shaft")
    assert math.dist(bar, _start(exercise)["bar_position_m"]) <= POSITION_TOL_M, bar


@needs_opensim
@pytest.mark.parametrize("exercise", PULLS)
def test_pulls_start_with_the_plates_on_the_floor(exercise: str) -> None:
    plate_radius = spec.exercise_spec(STD, exercise)["load"]["plate_diameter_m"] / 2
    bar_z = _station(exercise, "barbell_shaft")[2]
    assert bar_z == pytest.approx(plate_radius, abs=POSITION_TOL_M)


@needs_opensim
@pytest.mark.parametrize("exercise", PULLS)
def test_floor_pull_bar_height_above_lowest_sole(exercise: str) -> None:
    """The bar centre in floor-pull lifts is plate-radius above the lowest sole (#416)."""
    import opensim

    model, state = _engine(exercise)
    bar = model.getBodySet().get("barbell_shaft").getTransformInGround(state).p()
    geoms = model.getContactGeometrySet()
    lowest_y = float("inf")
    for i in range(geoms.getSize()):
        sphere = opensim.ContactSphere.safeDownCast(geoms.get(i))
        if sphere is None or not sphere.getName().startswith("foot_"):
            continue
        centre = sphere.getFrame().findStationLocationInGround(
            state, sphere.get_location()
        )
        bottom_y = centre.get(1) - sphere.getRadius()
        if bottom_y < lowest_y:
            lowest_y = bottom_y

    bar_height_above_sole = bar.get(1) - lowest_y
    plate_radius = spec.exercise_spec(STD, exercise)["load"]["plate_diameter_m"] / 2
    # The soles are seated their contact-law equilibrium depth into the floor
    # (#472), so the plates rest on the floor that much above the lowest sole.
    tree = ET.fromstring(EXERCISE_BUILDERS[exercise]()).find("Model")
    assert tree is not None
    seated = equilibrium_depth(contact_heights(tree), supported_weight(tree))
    assert bar_height_above_sole == pytest.approx(
        plate_radius + seated, abs=POSITION_TOL_M
    )


@needs_opensim
@pytest.mark.parametrize("exercise", LIFTS)
def test_palm_centres_close_on_the_bar(exercise: str) -> None:
    bar = _start(exercise)["bar_position_m"]
    half = spec.exercise_spec(STD, exercise)["grip"]["width_m"] / 2
    for side, sign in (("l", 1.0), ("r", -1.0)):
        want = (bar[0], bar[1] + sign * half, bar[2])
        gap = math.dist(_palm(exercise, side), want)
        assert gap <= GRIP_TOL_M, f"{exercise} {side}: palm {gap * 1000:.2f} mm off"


@needs_opensim
@pytest.mark.parametrize("exercise", LIFTS)
def test_feet_stand_flat_at_the_spec_stance(exercise: str) -> None:
    stance = spec.exercise_spec(STD, exercise)["stance"]
    ankle_z = topology.dimension(STD, STD["pose_frame"]["ankle_height_term"])
    for side, sign in (("l", 1.0), ("r", -1.0)):
        want = (
            STD["pose_frame"]["ankle_x_m"],
            sign * stance["foot_width_m"] / 2,
            ankle_z,
        )
        ankle = _station(exercise, f"foot_{side}")
        assert math.dist(ankle, want) <= FOOT_TOL_M, f"{side} ankle {ankle}"
        flat = topology.rpy_matrix(
            (0.0, 0.0, sign * math.radians(stance["toe_out_deg"]))
        )
        diff = _max_abs_diff(_rotation(exercise, f"foot_{side}"), flat)
        assert diff <= TOL["axis_angle_abs_rad"], f"{side} foot not flat ({diff})"


@needs_opensim
@pytest.mark.parametrize("exercise", LIFTS)
def test_soles_touch_the_floor(exercise: str) -> None:
    import opensim

    model, state = _engine(exercise)
    geoms = model.getContactGeometrySet()
    lows = []
    for i in range(geoms.getSize()):
        sphere = opensim.ContactSphere.safeDownCast(geoms.get(i))
        if sphere is None or not sphere.getName().startswith("foot_"):
            continue
        centre = sphere.getFrame().findStationLocationInGround(
            state, sphere.get_location()
        )
        lows.append(centre.get(1) - sphere.getRadius())
    assert len(lows) == 8
    assert min(lows) == pytest.approx(0.0, abs=FOOT_TOL_M)
    assert max(lows) == pytest.approx(0.0, abs=FOOT_TOL_M), "a foot is tilted"


@needs_opensim
@pytest.mark.parametrize("exercise", STANDING)
def test_combined_centre_of_mass_is_over_mid_foot(exercise: str) -> None:
    model, state = _engine(exercise)
    com = _canonical(model.calcMassCenterPosition(state))
    logger.info("%s start CoM (canonical) %s", exercise, com)
    offset = math.hypot(com[0], com[1])
    assert offset <= TOL["cross_engine_position_abs_m"], f"{exercise}: {com}"


@needs_opensim
def test_start_pose_scales_with_height() -> None:
    """Spec positions scale with height and angles do not: a 1.90 m lifter
    still closes the grip with the plates on the floor."""
    import opensim

    scale = 1.90 / STD["anthropometrics"]["height_m"]
    model, state = _engine("deadlift", 1.90)
    bodies = model.getBodySet()
    bar = _canonical(bodies.get("barbell_shaft").getPositionInGround(state))
    want = [scale * v for v in _start("deadlift")["bar_position_m"]]
    assert math.dist(bar, want) <= POSITION_TOL_M
    factor, term = STD["grip_point"]["origin"]["z"]
    palm_y = scale * factor * topology.dimension(STD, term)
    palm = _canonical(
        bodies.get("hand_l").findStationLocationInGround(
            state, opensim.Vec3(0, palm_y, 0)
        )
    )
    half = scale * spec.exercise_spec(STD, "deadlift")["grip"]["width_m"] / 2
    assert math.dist(palm, (want[0], want[1] + half, want[2])) <= GRIP_TOL_M


@needs_opensim
def test_bench_contact_force_at_the_start_pose_is_at_most_body_weight() -> None:
    """OpenSim_Models#384: the default bench state produced ~21.7 kN of contact.

    Each force element's contribution is logged; the fix is the spec pose and
    root placement, never stiffness or this bound.
    """
    import opensim

    model, state = _engine("bench_press")
    model.realizeAcceleration(state)
    forces = model.getForceSet()
    total_fy = 0.0
    for i in range(forces.getSize()):
        force = opensim.SmoothSphereHalfSpaceForce.safeDownCast(forces.get(i))
        if force is None:
            continue
        values = force.getRecordValues(state)
        fy = values.get(1)
        logger.info("bench_press %s Fy = %.3f N", force.getName(), fy)
        assert math.isfinite(fy), force.getName()
        total_fy += fy
    body_weight = STD["anthropometrics"]["body_mass_kg"] * G
    assert abs(total_fy) <= body_weight, f"summed contact Fy {total_fy:.1f} N"
